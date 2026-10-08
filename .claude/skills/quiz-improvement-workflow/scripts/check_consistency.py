"""問題ファイルと進捗ファイルの整合性を確認する。

使い方（リポジトリのルートで実行）:
    python .claude/skills/quiz-improvement-workflow/scripts/check_consistency.py A

確認すること:
- 問題ファイルの見出しの問題IDと、各周の進捗ファイルの問題IDが、同じ順序で一致するか
- 見出しの習熟レベルと、進捗ファイルの習熟レベルが一致するか
- 見出しに「欠番」を含む問題は数えない（枠だけ残した削除済みの問題）
- 問題ファイル冒頭の「問題数」と、実際の問題数が一致するか
- 進捗ファイルのサマリーのカテゴリ問題数と、実際の問題数が一致するか
- ねらい欄の未記入の問題（件数の表示のみ。不一致にはしない）
- 進捗ファイルの合計が、各カテゴリの問題数の和と一致するか
"""
import glob
import re
import sys

ID_PAT = r"[A-Z][0-9]?-\d{2}(?:-\d+)?"
LEVELS = ("知識確認", "理解確認", "応用")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def level_of(text):
    for lv in LEVELS:
        if lv in text:
            return lv
    return None


def main(cat):
    errors = []
    files = glob.glob(f"問題集/{cat}_*.md")
    if len(files) != 1:
        print(f"問題ファイルが特定できません: {files}")
        return 2
    qpath = files[0]
    qtext = read(qpath)

    questions = []
    for line in qtext.splitlines():
        m = re.match(rf"^## ({ID_PAT})(.*)$", line)
        if m and "欠番" in m.group(2):
            continue  # 欠番の見出しは問題として数えない
        if m and m.group(1).split("-")[0] == cat:
            questions.append((m.group(1), level_of(m.group(2))))
    ids = [q[0] for q in questions]
    print(f"{qpath}: {len(ids)}問 {ids}")

    # ねらい欄の記入状況（エラーにはしない。移行中は未記入が多いため、件数だけ表示する）
    blocks = re.split(r"(?m)^## ", qtext)[1:]
    missing = [
        re.match(ID_PAT, b).group(0) for b in blocks
        if re.match(ID_PAT, b) and "欠番" not in b.splitlines()[0] and "**ねらい**" not in b
    ]
    print(f"ねらい未記入: {len(missing)}問 {missing if missing else ''}")

    if len(set(ids)) != len(ids):
        errors.append(f"問題ファイルに重複IDがあります: {ids}")

    m = re.search(r"問題数[^0-9\n]*(\d+)問", qtext)
    if m and int(m.group(1)) != len(ids):
        errors.append(f"{qpath}: 冒頭の問題数 {m.group(1)} ≠ 実際 {len(ids)}")

    for ppath in sorted(glob.glob("問題集/進捗/第*周_進捗.md")):
        ptext = read(ppath)
        rows = []
        for line in ptext.splitlines():
            m = re.match(rf"^\| ({ID_PAT}) \| ([A-Z][0-9]?) \|(.*)$", line)
            if m and m.group(2) == cat:
                cols = [c.strip() for c in m.group(3).split("|")]
                rows.append((m.group(1), cols[1] if len(cols) > 1 else None))
        pids = [r[0] for r in rows]
        if pids != ids:
            errors.append(f"{ppath}: 問題IDが一致しません\n  問題ファイル: {ids}\n  進捗ファイル: {pids}")
        for (qid, qlv), (pid, plv) in zip(questions, rows):
            if qid == pid and qlv != plv:
                errors.append(f"{ppath}: {qid} の習熟レベル 問題ファイル={qlv} 進捗={plv}")

        summary = dict(
            (m.group(1), int(m.group(2)))
            for m in re.finditer(r"^\| ([A-Z][0-9]?) \| [^|]+ \| (\d+) \|", ptext, re.M)
        )
        if summary.get(cat) != len(ids):
            errors.append(f"{ppath}: サマリーの {cat} 問題数 {summary.get(cat)} ≠ 実際 {len(ids)}")
        m = re.search(r"\*\*合計\*\* \| \| \*\*(\d+)\*\*", ptext)
        if m and int(m.group(1)) != sum(summary.values()):
            errors.append(f"{ppath}: 合計 {m.group(1)} ≠ カテゴリ問題数の和 {sum(summary.values())}")

    if errors:
        print("\n不一致:")
        for e in errors:
            print("- " + e)
        return 1
    print("すべて一致しています。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
