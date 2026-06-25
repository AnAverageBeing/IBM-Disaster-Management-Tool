import subprocess
import shutil
from pathlib import Path
from ibm_dmt.core.logger import Logger


class Compressor:
    def __init__(self):
        self._log = Logger.get_logger()

    def compress(self, input_path: str, output_path: str = None) -> str:
        if output_path is None:
            output_path = f"{input_path}.zst"

        if shutil.which("zstd"):
            return self._compress_zstd(input_path, output_path)
        elif shutil.which("xz"):
            return self._compress_xz(input_path, output_path.replace(".zst", ".tar.xz"))
        elif shutil.which("7z"):
            return self._compress_7z(input_path, output_path.replace(".zst", ".7z"))
        else:
            import pyzstd
            return self._compress_pyzstd(input_path, output_path)

    def decompress(self, input_path: str, output_path: str = None) -> str:
        path = Path(input_path)
        if output_path is None:
            stem = path.stem
            if stem.endswith(".tar"):
                stem = Path(stem).stem
            output_path = str(path.parent / stem)

        suffix = path.suffix
        if suffix == ".zst":
            if shutil.which("zstd"):
                subprocess.run(["zstd", "-d", input_path, "-o", output_path], check=True)
            else:
                import pyzstd
                with open(input_path, "rb") as src, open(output_path, "wb") as dst:
                    pyzstd.decompress_stream(src, dst)
        elif suffix == ".xz":
            subprocess.run(["xz", "-d", input_path, "-o", output_path], check=True)
        elif suffix == ".7z":
            subprocess.run(["7z", "x", input_path, f"-o{output_path}"], check=True)

        return output_path

    def _compress_zstd(self, input_path: str, output_path: str) -> str:
        try:
            subprocess.run(["zstd", "-19", "--rm", "-o", output_path, input_path],
                           check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError:
            return self._compress_pyzstd(input_path, output_path)

    def _compress_xz(self, input_path: str, output_path: str) -> str:
        try:
            subprocess.run(["tar", "-cJf", output_path, input_path],
                           check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            self._log.error(f"xz compression failed: {e}")
            return input_path

    def _compress_7z(self, input_path: str, output_path: str) -> str:
        try:
            subprocess.run(["7z", "a", output_path, input_path, "-mx=9"],
                           check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            self._log.error(f"7z compression failed: {e}")
            return input_path

    def _compress_pyzstd(self, input_path: str, output_path: str) -> str:
        import pyzstd
        with open(input_path, "rb") as src, open(output_path, "wb") as dst:
            pyzstd.compress_stream(src, dst, level=19)
        return output_path
