import click
from pytbox.database.vm.backend import HTTPBackend, FileReplayBackend, RecordingBackend
from pytbox.database.vm.client import VictoriaMetricsClient
from pytbox.utils.richutils import RichUtils


rich_utils = RichUtils()


@click.group()
def vm_group():
    """VictoriaMetrics CLI 工具（查询/生成fixture/回放）"""
    pass


def _load_promql_lines(path: str) -> list[str]:
    """
    读取 promql 文件：一行一条
    - 自动忽略空行
    - 忽略以 # 开头的注释
    - 忽略像 '=== PromQL used ===' 这种分隔行
    """
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            if not s:
                continue
            if s.startswith("#"):
                continue
            if s.startswith("===") and s.endswith("==="):
                continue
            lines.append(s)
    return lines


@vm_group.command("record-promql")
@click.option("--url", "-u", required=True, help="VM base url，例如 http://vm:8428")
@click.option("--promql-file", "-f", required=True, type=click.Path(exists=True), help="PromQL 文件：一行一条")
@click.option("--out-dir", default="./fixtures/vm", show_default=True, help="fixture 输出目录")
@click.option("--timeout", default=10, show_default=True, type=int, help="HTTP 超时秒数")
@click.option("--no-overwrite", is_flag=True, help="fixture 已存在则不覆盖（需要后端支持；此处用跳过实现）")
def record_promql(url: str, promql_file: str, out_dir: str, timeout: int, no_overwrite: bool):
    """
    在生产环境执行 promql 文件中的查询，并保存 fixture
    """
    promqls = _load_promql_lines(promql_file)
    if not promqls:
        raise click.UsageError("promql 文件为空或没有有效行")

    http = HTTPBackend(url, timeout=timeout)
    replay = FileReplayBackend(out_dir)

    rich_utils.print(msg=f"Loaded {len(promqls)} promql(s) from: {promql_file}")
    rich_utils.print(msg=f"Saving fixtures to: {out_dir}")

    ok = 0
    fail = 0

    for idx, q in enumerate(promqls, start=1):
        try:
            # 如果你想“存在则不覆盖”，建议在 FileReplayBackend.save_fixture 支持 overwrite=False
            # 这里先简单实现：若 no_overwrite=True 且目标文件存在则跳过
            if no_overwrite:
                p = replay.path_for(q)
                if p.exists():
                    rich_utils.print(msg=f"[{idx}/{len(promqls)}] skip (exists): {p}")
                    ok += 1
                    continue

            raw = http.instant_query(q)
            p = replay.save_fixture(q, raw)  # 里面已写入 _fixture.promql 等信息（如果你按之前增强版实现）
            rich_utils.print(msg=f"[{idx}/{len(promqls)}] saved: {p}")
            ok += 1
        except Exception as e:
            rich_utils.print(msg=f"[{idx}/{len(promqls)}] failed: {q} | {e}")
            fail += 1

    rich_utils.print(msg=f"Done. ok={ok}, fail={fail}")


if __name__ == "__main__":
    vm()