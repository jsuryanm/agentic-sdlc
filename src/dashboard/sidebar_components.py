from html import escape
from typing import Sequence


PipelineStage = tuple[str, str, str]


def build_pipeline_html(
    pipeline_stages: Sequence[PipelineStage],
    stage: str,
    cur_idx: int,
) -> str:
    parts = ['<div class="af-pipe">']

    for idx, (_, name, desc) in enumerate(pipeline_stages):
        is_last = idx == len(pipeline_stages) - 1

        if stage == "done":
            node_cls = "complete"
        elif idx < cur_idx:
            node_cls = "complete"
        elif idx == cur_idx:
            node_cls = "active" if stage == "processing" else "complete"
        else:
            node_cls = ""

        line_cls = "complete" if idx < cur_idx or stage == "done" else ""
        name_cls = node_cls if node_cls else ""
        node_class_attr = f' class="af-pipe-node {node_cls}"' if node_cls else ' class="af-pipe-node"'
        line_html = (
            ""
            if is_last
            else (
                f'<div class="af-pipe-line {line_cls}"></div>'
                if line_cls
                else '<div class="af-pipe-line"></div>'
            )
        )
        name_class_attr = f' class="af-pipe-name {name_cls}"' if name_cls else ' class="af-pipe-name"'

        parts.extend(
            [
                '<div class="af-pipe-row">',
                '<div class="af-pipe-track">',
                f"<div{node_class_attr}></div>",
                line_html,
                "</div>",
                '<div class="af-pipe-info">',
                f"<div{name_class_attr}>{escape(name)}</div>",
                f'<div class="af-pipe-desc">{escape(desc)}</div>',
                "</div>",
                "</div>",
            ]
        )

    parts.append("</div>")
    return "".join(parts)
