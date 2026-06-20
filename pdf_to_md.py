#!/usr/bin/env python3
"""
Convierte archivos PDF a Markdown (.md).
Extrae: texto con jerarquía, tablas, imágenes (con OCR si es necesario).
"""

import sys
import os
import re
import argparse
from pathlib import Path

import fitz          # pymupdf
import pdfplumber
from PIL import Image
import pytesseract


def limpiar_texto(texto: str) -> str:
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


def detectar_nivel_titulo(span: dict) -> int | None:
    """Devuelve 1-4 según tamaño de fuente, o None si es texto normal."""
    size = span.get("size", 0)
    bold = "Bold" in span.get("font", "")
    if size >= 20:
        return 1
    if size >= 16:
        return 2
    if size >= 13 and bold:
        return 3
    if size >= 11 and bold:
        return 4
    return None


def extraer_texto_estructurado(pagina_fitz) -> str:
    """Extrae texto con formato Markdown usando tamaños de fuente."""
    bloques = pagina_fitz.get_text("dict")["blocks"]
    lineas_md = []

    for bloque in bloques:
        if bloque.get("type") != 0:  # 0 = texto
            continue
        for linea in bloque.get("lines", []):
            contenido = ""
            nivel = None
            for span in linea.get("spans", []):
                texto = span["text"].strip()
                if not texto:
                    continue
                nivel = detectar_nivel_titulo(span) or nivel
                bold = "Bold" in span.get("font", "")
                italic = "Italic" in span.get("font", "")
                if bold and italic:
                    texto = f"***{texto}***"
                elif bold:
                    texto = f"**{texto}**"
                elif italic:
                    texto = f"*{texto}*"
                contenido += texto + " "

            contenido = contenido.strip()
            if not contenido:
                continue
            if nivel:
                lineas_md.append(f"{'#' * nivel} {contenido}")
            else:
                lineas_md.append(contenido)

    return "\n\n".join(lineas_md)


def extraer_tablas(pagina_plumber) -> list[str]:
    """Extrae tablas y las convierte a formato Markdown."""
    tablas_md = []
    for tabla in pagina_plumber.extract_tables():
        if not tabla:
            continue
        filas = [[str(c) if c else "" for c in fila] for fila in tabla]
        if not filas:
            continue

        encabezado = filas[0]
        separador = ["---"] * len(encabezado)
        cuerpo = filas[1:]

        md = "| " + " | ".join(encabezado) + " |\n"
        md += "| " + " | ".join(separador) + " |\n"
        for fila in cuerpo:
            md += "| " + " | ".join(fila) + " |\n"
        tablas_md.append(md)

    return tablas_md


def extraer_imagenes(pagina_fitz, doc_fitz, num_pagina: int, carpeta_imgs: Path) -> list[str]:
    """Extrae imágenes de la página, aplica OCR y guarda los archivos."""
    carpeta_imgs.mkdir(parents=True, exist_ok=True)
    imagenes_md = []

    for i, img_info in enumerate(pagina_fitz.get_images(full=True)):
        xref = img_info[0]
        try:
            base_img = doc_fitz.extract_image(xref)
            img_bytes = base_img["image"]
            ext = base_img["ext"]
            nombre = f"pagina{num_pagina + 1}_img{i + 1}.{ext}"
            ruta = carpeta_imgs / nombre

            with open(ruta, "wb") as f:
                f.write(img_bytes)

            # OCR a la imagen
            try:
                pil_img = Image.open(ruta)
                ocr_texto = pytesseract.image_to_string(pil_img).strip()
            except Exception:
                ocr_texto = ""

            ref = f"imgs/{nombre}"
            if ocr_texto:
                imagenes_md.append(f"![imagen]({ref})\n\n> {ocr_texto}")
            else:
                imagenes_md.append(f"![imagen]({ref})")

        except Exception as e:
            imagenes_md.append(f"<!-- Error extrayendo imagen {i+1}: {e} -->")

    return imagenes_md


def pdf_a_markdown(ruta_pdf: str, ruta_salida: str | None = None) -> str:
    ruta_pdf = Path(ruta_pdf)
    if not ruta_pdf.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_pdf}")

    if ruta_salida is None:
        ruta_salida = ruta_pdf.with_suffix(".md")
    else:
        ruta_salida = Path(ruta_salida)

    carpeta_imgs = ruta_salida.parent / "imgs"
    secciones = [f"# {ruta_pdf.stem}\n"]

    doc_fitz = fitz.open(str(ruta_pdf))

    with pdfplumber.open(str(ruta_pdf)) as doc_plumber:
        for num, (pag_fitz, pag_plumber) in enumerate(
            zip(doc_fitz, doc_plumber.pages)
        ):
            secciones.append(f"\n---\n## Página {num + 1}\n")

            # Texto estructurado
            texto = extraer_texto_estructurado(pag_fitz)
            if texto:
                secciones.append(limpiar_texto(texto))

            # Tablas
            tablas = extraer_tablas(pag_plumber)
            for tabla in tablas:
                secciones.append("\n**Tabla:**\n\n" + tabla)

            # Imágenes + OCR
            imagenes = extraer_imagenes(pag_fitz, doc_fitz, num, carpeta_imgs)
            for img_md in imagenes:
                secciones.append(img_md)

    doc_fitz.close()

    contenido_final = "\n\n".join(secciones)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(contenido_final)

    return str(ruta_salida)


def main():
    parser = argparse.ArgumentParser(
        description="Convierte PDF a Markdown (.md)"
    )
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument(
        "-o", "--output", help="Ruta de salida del .md (opcional)"
    )
    args = parser.parse_args()

    print(f"Procesando: {args.pdf}")
    salida = pdf_a_markdown(args.pdf, args.output)
    print(f"Archivo Markdown generado: {salida}")


if __name__ == "__main__":
    main()
