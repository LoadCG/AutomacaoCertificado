"""
Script de geração do ícone da aplicação.

Gera um arquivo .ico com múltiplos tamanhos (16, 32, 48, 256px)
compatível com Windows Explorer e barra de tarefas.

Uso:
    python scripts/gerar_icone.py
"""

from pathlib import Path

DESTINO_PADRAO = Path(__file__).parent.parent / "assets" / "icon.ico"


def gerar_icone(destino: Path = DESTINO_PADRAO) -> None:
    """
    Gera o ícone se não existir no destino.

    Cria um ícone azul com cantos arredondados e a letra 'G' centralizada,
    nos tamanhos 16, 32, 48 e 256px exigidos pelo Windows.

    Args:
        destino: Caminho de saída do arquivo .ico.
    """
    if destino.exists():
        print(f"Ícone já existe: {destino}")
        return

    from PIL import Image, ImageDraw, ImageFont

    destino.parent.mkdir(parents=True, exist_ok=True)

    tamanhos = [16, 32, 48, 256]
    imagens = []

    for tam in tamanhos:
        img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        raio = tam // 6
        draw.rounded_rectangle(
            [2, 2, tam - 2, tam - 2],
            radius=raio,
            fill="#1E90FF",
        )

        # Letra S centralizada
        tamanho_fonte = max(int(tam * 0.55), 8)
        try:
            fonte = ImageFont.truetype("segoeui.ttf", tamanho_fonte)
        except (OSError, IOError):
            fonte = ImageFont.load_default()

        draw.text(
            (tam // 2, tam // 2),
            "G",
            fill="white",
            font=fonte,
            anchor="mm",
        )
        imagens.append(img)

    imagens[0].save(
        destino,
        format="ICO",
        sizes=[(t, t) for t in tamanhos],
        append_images=imagens[1:],
    )
    print(f"Ícone gerado: {destino}")


if __name__ == "__main__":
    gerar_icone()
