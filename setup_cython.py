#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARAMe Manager - Cython 컴파일 스크립트
소스코드 보호를 위해 Python 코드를 C 확장으로 컴파일합니다.
"""

import os
import sys
import glob
import shutil
from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

print("=" * 60)
print("  GARAMe Manager - Cython 컴파일")
print("  소스코드 보호 빌드")
print("=" * 60)
print()

# 컴파일할 Python 파일 목록
def find_python_files():
    """컴파일할 .py 파일 찾기"""
    py_files = []

    # src 디렉토리의 모든 .py 파일
    src_files = glob.glob("src/**/*.py", recursive=True)
    py_files.extend(src_files)

    # 최상위 디렉토리의 주요 파일들
    top_level_files = [
        "main.py",
        "watchdog.py",
    ]

    for f in top_level_files:
        if os.path.exists(f):
            py_files.append(f)

    # 제외할 파일들 (__init__.py는 유지)
    exclude_patterns = [
        "test_",
        "setup",
        "build",
    ]

    filtered_files = []
    for f in py_files:
        exclude = False
        for pattern in exclude_patterns:
            if pattern in f:
                exclude = True
                break
        if not exclude:
            filtered_files.append(f)

    return filtered_files

# Extension 모듈 생성
def create_extensions():
    """Cython Extension 모듈 생성"""
    py_files = find_python_files()

    print(f"컴파일할 파일: {len(py_files)}개")
    for f in py_files:
        print(f"  - {f}")
    print()

    extensions = []
    for py_file in py_files:
        # 모듈 이름 생성 (경로를 모듈명으로 변환)
        module_name = py_file.replace("/", ".").replace("\\", ".").replace(".py", "")

        ext = Extension(
            module_name,
            [py_file],
            extra_compile_args=["-O3"],  # 최적화 레벨 3
        )
        extensions.append(ext)

    return extensions

# 컴파일러 지시어
compiler_directives = {
    'language_level': "3",           # Python 3
    'embedsignature': False,         # 디버그 정보 제거
    'boundscheck': False,            # 경계 검사 비활성화 (성능 향상)
    'wraparound': False,             # 음수 인덱스 비활성화 (성능 향상)
    'initializedcheck': False,       # 초기화 검사 비활성화
    'cdivision': True,               # C 나눗셈 사용 (성능 향상)
    'always_allow_keywords': False,  # 키워드 인자 비활성화 (성능 향상)
}

# Setup 실행
if __name__ == "__main__":
    try:
        extensions = create_extensions()

        setup(
            name="GARAMe Manager",
            version="1.9.7",
            description="GARAMe Manager - Cythonized Version",
            ext_modules=cythonize(
                extensions,
                compiler_directives=compiler_directives,
                build_dir="build",
                language_level=3,
            ),
            cmdclass={'build_ext': build_ext},
            zip_safe=False,
        )

        print()
        print("=" * 60)
        print("  컴파일 완료!")
        print("=" * 60)
        print()
        print("다음 단계:")
        print("  1. build_secure.sh 실행으로 .py 파일 제거 및 정리")
        print("  2. run.sh로 프로그램 실행")
        print()

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
