"""Chạy cả chuỗi xử lý dữ liệu bằng một lệnh.

    python run_pipeline.py                    # dùng mẫu có sẵn, dựng lại kho, chạy kiểm thử
    python run_pipeline.py --refresh-sample   # lấy mẫu mới từ Hugging Face (tải vài GB)
    python run_pipeline.py --skip-tests       # bỏ qua bước kiểm thử
    python run_pipeline.py --dashboard        # chạy xong thì mở dashboard
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402


def run(title, cmd):
    print(f"\n=== {title} ===", flush=True)
    start = time.time()
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"\nBước '{title}' thất bại (mã lỗi {result.returncode}). Pipeline dừng lại.")
    print(f"[xong sau {time.time() - start:.0f} giây]", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Pipeline dữ liệu cờ vua Lichess")
    parser.add_argument("--refresh-sample", action="store_true", help="lấy lại mẫu từ Hugging Face")
    parser.add_argument("--skip-tests", action="store_true", help="bỏ qua bước kiểm thử")
    parser.add_argument("--dashboard", action="store_true", help="mở dashboard sau khi xong")
    args = parser.parse_args()

    py = sys.executable

    if args.refresh_sample or not config.SAMPLE_FILE.exists():
        run("1. Lấy mẫu dữ liệu từ Hugging Face", [py, "src/ingest.py"])
    else:
        print(f"Bỏ qua bước lấy mẫu vì đã có {config.SAMPLE_FILE.name} "
              "(thêm --refresh-sample nếu muốn lấy lại).")

    run("2. Nạp, làm sạch và tạo cột trong DuckDB", [py, "src/build_warehouse.py"])

    if not args.skip_tests:
        run("3. Kiểm thử kho dữ liệu", [py, "-m", "pytest", "-q"])

    print("\nPipeline hoàn tất. Chạy dashboard bằng: streamlit run dashboard/app.py")

    if args.dashboard:
        run("4. Dashboard (Ctrl+C để dừng)", [py, "-m", "streamlit", "run", "dashboard/app.py"])


if __name__ == "__main__":
    main()