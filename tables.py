import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

NO_AMBIGUITY = "No_Ambiguity"

# 9 Taxonomy subtypes + baseline unambiguous class
ALL_SUBTYPES = [
    NO_AMBIGUITY,
    "Scope",
    "Attachment",
    "Intent",
    "Temporal",
    "Column",
    "Table",
    "Join",
    "Aggregate",
    "Value",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate LaTeX Confusion Matrix and Metrics Table from Evaluation JSON"
    )
    parser.add_argument(
        "json_file",
        type=str,
        help="Path to evaluation JSON output (e.g. outputs/timestamp.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tables",
        help="Directory to save generated LaTeX tables",
    )
    return parser.parse_args()


def extract_pairs_from_query(entry):
    raw_exp = entry.get("expected_ambiguities", [])
    raw_act = entry.get("ambiguities", [])

    if not isinstance(raw_act, list):
        raw_act = []

    expected_pool = [
        a["subtype"]
        for a in raw_exp
        if isinstance(a, dict) and a.get("subtype") in ALL_SUBTYPES
    ]
    predicted_pool = [
        a["subtype"]
        for a in raw_act
        if isinstance(a, dict) and a.get("subtype") in ALL_SUBTYPES
    ]

    exp_objs = [
        dict(a)
        for a in raw_exp
        if isinstance(a, dict) and a.get("subtype") in ALL_SUBTYPES
    ]
    act_objs = [
        dict(a)
        for a in raw_act
        if isinstance(a, dict) and a.get("subtype") in ALL_SUBTYPES
    ]

    y_true_query = []
    y_pred_query = []

    # Case 1: Clean query
    if len(expected_pool) == 0:
        if len(predicted_pool) == 0:
            return [NO_AMBIGUITY], [NO_AMBIGUITY]
        else:
            for pred_sub in predicted_pool:
                y_true_query.append(NO_AMBIGUITY)
                y_pred_query.append(pred_sub)
            return y_true_query, y_pred_query

    # Case 2: Complete miss
    if len(predicted_pool) == 0:
        for exp_sub in expected_pool:
            y_true_query.append(exp_sub)
            y_pred_query.append(NO_AMBIGUITY)
        return y_true_query, y_pred_query

    # Case 3: Alignments
    # 3a. Exact subtype matches
    for exp in list(exp_objs):
        match = next(
            (act for act in act_objs if act.get("subtype") == exp.get("subtype")),
            None,
        )
        if match:
            y_true_query.append(exp["subtype"])
            y_pred_query.append(match["subtype"])
            exp_objs.remove(exp)
            act_objs.remove(match)

    # 3b. Coarse parent type fallback
    for exp in list(exp_objs):
        match = next(
            (act for act in act_objs if act.get("type") == exp.get("type")),
            None,
        )
        if match:
            y_true_query.append(exp["subtype"])
            y_pred_query.append(match["subtype"])
            exp_objs.remove(exp)
            act_objs.remove(match)

    # 3c. Remaining discrepancies
    while exp_objs and act_objs:
        e = exp_objs.pop(0)
        a = act_objs.pop(0)
        y_true_query.append(e["subtype"])
        y_pred_query.append(a["subtype"])

    # 3d. Unmatched gold items (missed)
    for e in exp_objs:
        y_true_query.append(e["subtype"])
        y_pred_query.append(NO_AMBIGUITY)

    # 3e. Unmatched predicted items (hallucinated)
    for a in act_objs:
        y_true_query.append(NO_AMBIGUITY)
        y_pred_query.append(a["subtype"])

    return y_true_query, y_pred_query


def generate_latex_matrix(cm_norm, labels):
    """Formats the row-normalized confusion matrix to match the target layout."""
    col_spec = "l" + "r" * len(labels)
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \small",
        r"  \setlength{\tabcolsep}{4pt}",
        r"  \begin{tabular}{" + col_spec + r"}",
    ]

    header = (
        r"    \makecell{Expected \\ / \\ Predicted} & "
        + " & ".join([r"\rotatebox{60}{" + l + "}" for l in labels])
        + r" \\"
    )
    lines.append(header)
    lines.append(r"    \midrule")

    for i, row_label in enumerate(labels):
        row_vals = []
        for val in cm_norm[i]:
            intensity = int(round(val * 60))
            if intensity > 0:
                cell_str = f"\\cellcolor{{blue!{intensity}}}{val:.2f}"
            else:
                cell_str = "0.00"
            row_vals.append(cell_str)

        row_str = f"    {row_label:<14} & " + " & ".join(row_vals) + r" \\"
        lines.append(row_str)

    lines.append(r"  \end{tabular}")
    lines.append(
        r"  \caption{Row-normalized confusion matrix across ambiguity subtypes and clean queries (\textit{No Ambiguity}). Rows represent ground-truth annotations, while columns represent system predictions. Cell shading indicates the proportion of predictions within each ground-truth class.}"
    )
    lines.append(r"  \label{tab:subtype_confusion_matrix}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


def generate_latex_metrics_table(report_df):
    """Outputs precision, recall, and f1-score with centered columns, excluding support."""
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \begin{tabular}{l c c c}",
        r"    & precision & recall & f1-score \\",
        r"    \midrule",
    ]

    for label, row in report_df.iterrows():
        lines.append(
            f"    {label:<14} & {row['precision']:.2f} & {row['recall']:.2f} & {row['f1-score']:.2f} \\\\"
        )

    lines.append(r"  \end{tabular}")
    lines.append(
        r"  \caption{Per-subtype ambiguity classification performance metrics.}"
    )
    lines.append(r"  \label{tab:subtype_metrics}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


def generate_unified_latex_table(df_metrics, eval_data, labels):
    """Generates a clean summary results table matching the exact layout."""
    type_metrics = eval_data.get("type_metrics", {})
    type_p = type_metrics.get("precision", 0.0)
    type_r = type_metrics.get("recall", 0.0)
    type_f1 = type_metrics.get("f1", 0.0)

    amb_count = eval_data.get("ambiguity_count", {})
    accuracy = amb_count.get("accuracy", 0.0)

    macro_p = df_metrics["precision"].mean()
    macro_r = df_metrics["recall"].mean()
    macro_f1 = df_metrics["f1-score"].mean()

    lines = [
        r"\begin{table}[htbp]",
        r"    \centering",
        r"    \begin{tabular}{lccc}",
        r"        & Precision & Recall & $F_1$-score \\",
        r"        \midrule",
    ]

    # Subtype rows with fixed label width padding
    for label in labels:
        p = df_metrics.loc[label, "precision"]
        r = df_metrics.loc[label, "recall"]
        f1 = df_metrics.loc[label, "f1-score"]
        lines.append(
            f"        {label:<12} & {p:.2f} & {r:.2f} & {f1:.2f} \\\\"
        )

    lines.append(r"        \midrule")

    # Summary rows
    lines.append(
        f"        \\textbf{{Subtype (Macro)}} & \\textbf{{{macro_p:.2f}}} & \\textbf{{{macro_r:.2f}}} & \\textbf{{{macro_f1:.2f}}} \\\\"
    )
    lines.append(
        f"        \\textbf{{Type (Coarse)}}   & \\textbf{{{type_p:.2f}}} & \\textbf{{{type_r:.2f}}} & \\textbf{{{type_f1:.2f}}} \\\\"
    )
    lines.append(
        f"        \\textbf{{Exact Count Acc.}} & \\multicolumn{{3}}{{c}}{{\\textbf{{{accuracy:.2f}}}}} \\\\"
    )

    lines.append(r"    \end{tabular}")
    lines.append(
        r"    \caption{Overall ambiguity classification results, including per-subtype performance, macro averages, coarse type-level metrics, and exact ambiguity count accuracy.}"
    )
    lines.append(r"    \label{tab:unified_evaluation_summary}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract dataset queries and the precomputed evaluation block
    results = data.get("results", data) if isinstance(data, dict) else data
    eval_data = data.get("evaluation", {}) if isinstance(data, dict) else {}

    y_true = []
    y_pred = []

    for entry in results:
        yt, yp = extract_pairs_from_query(entry)
        y_true.extend(yt)
        y_pred.extend(yp)

    print(
        f"Aligned {len(results)} queries into {len(y_true)} classification instances."
    )

    clean_labels = [s.replace("_", " ") for s in ALL_SUBTYPES]

    # 1. Row-normalized Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=ALL_SUBTYPES)
    row_sums = cm.sum(axis=1)[:, np.newaxis]
    cm_norm = np.divide(
        cm.astype("float"),
        row_sums,
        out=np.zeros_like(cm, dtype=float),
        where=row_sums != 0,
    )

    matrix_latex = generate_latex_matrix(cm_norm, clean_labels)
    matrix_path = out_dir / "subtype_confusion_matrix.tex"
    with open(matrix_path, "w", encoding="utf-8") as f:
        f.write(matrix_latex)
    print(f"Saved LaTeX confusion matrix to: {matrix_path}")

    # 2. Classification Metrics Table
    report = classification_report(
        y_true,
        y_pred,
        labels=ALL_SUBTYPES,
        target_names=clean_labels,
        output_dict=True,
        zero_division=0,
    )

    df_metrics = pd.DataFrame(report).T.loc[
        clean_labels, ["precision", "recall", "f1-score", "support"]
    ]

    metrics_latex = generate_latex_metrics_table(df_metrics)
    metrics_path = out_dir / "subtype_metrics_table.tex"
    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write(metrics_latex)
    print(f"Saved LaTeX metrics table to: {metrics_path}")

    # 3. Master Unified Table (using eval_data)
    unified_latex = generate_unified_latex_table(
        df_metrics=df_metrics,
        eval_data=eval_data,
        labels=clean_labels,
    )
    unified_path = out_dir / "unified_evaluation_table.tex"
    with open(unified_path, "w", encoding="utf-8") as f:
        f.write(unified_latex)
    print(f"Saved unified LaTeX evaluation table to: {unified_path}")


if __name__ == "__main__":
    main()