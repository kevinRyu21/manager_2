"""
안전교육 기록 무결성 관리 모듈

특허 청구항 관련:
- 청구항 1(f): 해시 체인 기반 무결성 검증
- 청구항 2: 메타데이터 JSON 생성
- 청구항 6(g): 체인 해시 생성 방법
- 청구항 9: 무결성 검증 방법

기능:
- SHA-256 해시 생성
- 해시 체인 관리 (블록체인 유사)
- 기록 무결성 검증
- 반출 아카이브 생성
"""

import hashlib
import json
import os
import shutil
import zipfile
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from .helpers import get_base_dir


class IntegrityManager:
    """
    해시 체인 기반 무결성 관리자

    각 안전교육 기록에 대해:
    1. 개별 파일 해시 계산
    2. 통합 해시 생성 (모든 파일 해시 결합)
    3. 체인 해시 생성 (통합 해시 + 이전 기록 체인 해시)

    이를 통해 기록의 삽입, 삭제, 변조를 탐지할 수 있음.
    """

    # 최초 기록의 이전 해시 (제네시스 해시)
    GENESIS_HASH = "0" * 64
    HASH_ALGORITHM = "SHA-256"
    VERSION = "1.0"

    def __init__(self, data_dir: str = None):
        """
        초기화

        Args:
            data_dir: 데이터 저장 디렉토리 (기본값: safety_photos)
        """
        if data_dir is None:
            # 프로그램 설치 디렉토리 기준으로 경로 설정
            install_dir = get_base_dir()
            data_dir = os.path.join(install_dir, "safety_photos")

        self.data_dir = data_dir
        self.chain_file = os.path.join(data_dir, "hash_chain.json")
        self._lock = threading.Lock()

        # 디렉토리 생성
        os.makedirs(data_dir, exist_ok=True)

        # 체인 데이터 로드
        self.chain = self._load_chain()

    # =========================================================================
    # 해시 체인 파일 관리
    # =========================================================================

    def _load_chain(self) -> Dict:
        """
        해시 체인 파일 로드

        Returns:
            체인 데이터 딕셔너리
        """
        if os.path.exists(self.chain_file):
            try:
                with open(self.chain_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 버전 호환성 체크
                    if data.get("version") != self.VERSION:
                        print(f"[IntegrityManager] 체인 버전 불일치: {data.get('version')} != {self.VERSION}")
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"[IntegrityManager] 체인 파일 로드 실패: {e}")
                # 백업 후 새로 생성
                if os.path.exists(self.chain_file):
                    backup_path = self.chain_file + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.chain_file, backup_path)
                    print(f"[IntegrityManager] 기존 체인 파일 백업: {backup_path}")

        # 새 체인 생성
        return self._create_new_chain()

    def _create_new_chain(self) -> Dict:
        """
        새 해시 체인 생성

        Returns:
            초기화된 체인 데이터
        """
        return {
            "version": self.VERSION,
            "hash_algorithm": self.HASH_ALGORITHM,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_records": 0,
            "genesis_hash": self.GENESIS_HASH,
            "records": [],
            "export_history": []  # 반출 이력
        }

    def _save_chain(self) -> bool:
        """
        해시 체인 파일 저장

        Note: 이 메서드는 이미 락이 획득된 상태에서 호출되므로
              내부에서 락을 다시 획득하지 않음 (데드락 방지)

        Returns:
            저장 성공 여부
        """
        # 주의: add_record() 등에서 이미 self._lock을 획득한 상태로 호출됨
        # threading.Lock()은 재진입을 지원하지 않으므로 여기서 락을 걸면 데드락 발생
        try:
            self.chain["last_updated"] = datetime.now().isoformat()
            self.chain["total_records"] = len(self.chain["records"])

            # 임시 파일에 먼저 저장 후 이동 (원자적 쓰기)
            temp_file = self.chain_file + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.chain, f, ensure_ascii=False, indent=2)

            # 기존 파일 교체
            if os.path.exists(self.chain_file):
                os.replace(temp_file, self.chain_file)
            else:
                os.rename(temp_file, self.chain_file)

            return True

        except IOError as e:
            print(f"[IntegrityManager] 체인 파일 저장 실패: {e}")
            return False

    # =========================================================================
    # 해시 계산
    # =========================================================================

    def calculate_file_hash(self, filepath: str) -> Optional[str]:
        """
        파일의 SHA-256 해시 계산

        Args:
            filepath: 파일 경로

        Returns:
            해시 문자열 (64자 hex) 또는 None
        """
        if not os.path.exists(filepath):
            print(f"[IntegrityManager] 파일 없음: {filepath}")
            return None

        try:
            hash_obj = hashlib.sha256()
            with open(filepath, 'rb') as f:
                # 대용량 파일 처리를 위해 청크 단위로 읽기
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except IOError as e:
            print(f"[IntegrityManager] 파일 해시 계산 실패: {filepath} - {e}")
            return None

    def calculate_data_hash(self, data: bytes) -> str:
        """
        바이트 데이터의 SHA-256 해시 계산

        Args:
            data: 바이트 데이터

        Returns:
            해시 문자열 (64자 hex)
        """
        return hashlib.sha256(data).hexdigest()

    def calculate_string_hash(self, text: str) -> str:
        """
        문자열의 SHA-256 해시 계산

        Args:
            text: 문자열

        Returns:
            해시 문자열 (64자 hex)
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def calculate_combined_hash(self, file_hashes: Dict[str, str]) -> str:
        """
        여러 파일 해시를 결합한 통합 해시 계산

        Args:
            file_hashes: {"파일명": "해시값", ...}

        Returns:
            통합 해시 문자열
        """
        # 파일명 순서로 정렬하여 일관성 보장
        sorted_hashes = sorted(file_hashes.items(), key=lambda x: x[0])

        # 모든 해시를 연결
        combined = "".join([h for _, h in sorted_hashes])

        return self.calculate_string_hash(combined)

    def calculate_chain_hash(self, combined_hash: str, previous_chain_hash: str) -> str:
        """
        체인 해시 계산 (통합해시 + 이전 체인 해시)

        Args:
            combined_hash: 현재 기록의 통합 해시
            previous_chain_hash: 이전 기록의 체인 해시

        Returns:
            새 체인 해시
        """
        return self.calculate_string_hash(combined_hash + previous_chain_hash)

    # =========================================================================
    # 기록 관리
    # =========================================================================

    def get_last_chain_hash(self) -> str:
        """
        마지막 기록의 체인 해시 반환

        Returns:
            마지막 체인 해시 (기록이 없으면 GENESIS_HASH)
        """
        if not self.chain["records"]:
            return self.GENESIS_HASH

        return self.chain["records"][-1].get("chain_hash", self.GENESIS_HASH)

    def get_next_record_id(self) -> str:
        """
        다음 기록 ID 생성

        Returns:
            기록 ID (예: REC-20251127-091532-001)
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # 같은 초에 여러 기록이 생성될 경우를 위한 시퀀스 번호
        sequence = 1
        for record in reversed(self.chain["records"]):
            if record["record_id"].startswith(f"REC-{timestamp}"):
                # 기존 시퀀스 번호 추출
                try:
                    existing_seq = int(record["record_id"].split("-")[-1])
                    sequence = existing_seq + 1
                except (ValueError, IndexError):
                    pass
                break

        return f"REC-{timestamp}-{sequence:03d}"

    def add_record(self, files: Dict[str, str], metadata: Dict[str, Any]) -> Dict:
        """
        새 기록 추가 및 체인 해시 생성

        Args:
            files: {"파일유형": "파일경로", ...}
                   예: {"combined_image": "/path/to/image.jpg", "metadata": "/path/to/meta.json"}
            metadata: 추가 메타데이터 (person_name 등)

        Returns:
            생성된 기록 정보
        """
        with self._lock:
            record_id = self.get_next_record_id()
            timestamp = datetime.now().isoformat()

            # 1. 각 파일의 해시 계산
            file_hashes = {}
            file_info = {}

            for file_type, filepath in files.items():
                if filepath and os.path.exists(filepath):
                    file_hash = self.calculate_file_hash(filepath)
                    if file_hash:
                        filename = os.path.basename(filepath)
                        file_hashes[filename] = file_hash
                        file_info[file_type] = {
                            "filename": filename,
                            "path": filepath,
                            "hash": file_hash
                        }

            if not file_hashes:
                raise ValueError("유효한 파일이 없습니다.")

            # 2. 통합 해시 계산
            combined_hash = self.calculate_combined_hash(file_hashes)

            # 3. 이전 체인 해시 가져오기
            previous_chain_hash = self.get_last_chain_hash()

            # 4. 체인 해시 계산
            chain_hash = self.calculate_chain_hash(combined_hash, previous_chain_hash)

            # 5. 기록 생성
            record = {
                "record_id": record_id,
                "timestamp": timestamp,
                "person_name": metadata.get("person_name"),
                "files": file_info,
                "combined_hash": combined_hash,
                "previous_chain_hash": previous_chain_hash,
                "chain_hash": chain_hash
            }

            # 6. 체인에 추가
            self.chain["records"].append(record)

            # 7. 체인 파일 저장
            self._save_chain()

            print(f"[IntegrityManager] 기록 추가 완료: {record_id}")

            return record

    def get_record(self, record_id: str) -> Optional[Dict]:
        """
        기록 ID로 기록 조회

        Args:
            record_id: 기록 ID

        Returns:
            기록 정보 또는 None
        """
        for record in self.chain["records"]:
            if record["record_id"] == record_id:
                return record
        return None

    def get_records_by_date(self, start_date: str, end_date: str) -> List[Dict]:
        """
        날짜 범위로 기록 조회

        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            기록 목록
        """
        results = []

        start_dt = datetime.fromisoformat(start_date + "T00:00:00")
        end_dt = datetime.fromisoformat(end_date + "T23:59:59")

        for record in self.chain["records"]:
            record_dt = datetime.fromisoformat(record["timestamp"])
            if start_dt <= record_dt <= end_dt:
                results.append(record)

        return results

    # =========================================================================
    # 무결성 검증
    # =========================================================================

    def verify_record(self, record_id: str) -> Tuple[bool, str, Dict]:
        """
        단일 기록 무결성 검증

        Args:
            record_id: 기록 ID

        Returns:
            (성공여부, 메시지, 상세정보)
        """
        record = self.get_record(record_id)
        if not record:
            return False, f"기록을 찾을 수 없습니다: {record_id}", {}

        details = {
            "record_id": record_id,
            "timestamp": record["timestamp"],
            "person_name": record.get("person_name"),
            "file_checks": [],
            "combined_hash_valid": False,
            "chain_hash_valid": False
        }

        # 1. 각 파일 해시 검증
        file_hashes = {}
        all_files_valid = True

        for file_type, file_info in record.get("files", {}).items():
            filepath = file_info.get("path")
            stored_hash = file_info.get("hash")

            if not filepath or not os.path.exists(filepath):
                details["file_checks"].append({
                    "file_type": file_type,
                    "filename": file_info.get("filename"),
                    "status": "missing",
                    "message": "파일이 존재하지 않습니다"
                })
                all_files_valid = False
                continue

            current_hash = self.calculate_file_hash(filepath)
            filename = file_info.get("filename")

            if current_hash == stored_hash:
                details["file_checks"].append({
                    "file_type": file_type,
                    "filename": filename,
                    "status": "valid",
                    "message": "정상"
                })
                file_hashes[filename] = current_hash
            else:
                details["file_checks"].append({
                    "file_type": file_type,
                    "filename": filename,
                    "status": "modified",
                    "message": "파일이 변조되었습니다",
                    "stored_hash": stored_hash[:16] + "...",
                    "current_hash": current_hash[:16] + "..."
                })
                all_files_valid = False

        if not all_files_valid:
            return False, "파일 무결성 검증 실패", details

        # 2. 통합 해시 검증
        current_combined = self.calculate_combined_hash(file_hashes)
        stored_combined = record.get("combined_hash")

        if current_combined == stored_combined:
            details["combined_hash_valid"] = True
        else:
            return False, "통합 해시 불일치", details

        # 3. 체인 해시 검증
        stored_chain = record.get("chain_hash")
        previous_chain = record.get("previous_chain_hash")
        current_chain = self.calculate_chain_hash(current_combined, previous_chain)

        if current_chain == stored_chain:
            details["chain_hash_valid"] = True
        else:
            return False, "체인 해시 불일치", details

        return True, "무결성 검증 통과", details

    def verify_chain(self, start_index: int = 0, end_index: int = None) -> Tuple[bool, List[Dict]]:
        """
        해시 체인 연속성 검증

        Args:
            start_index: 시작 인덱스 (기본값: 0)
            end_index: 종료 인덱스 (기본값: 마지막)

        Returns:
            (성공여부, 검증결과목록)
        """
        records = self.chain["records"]

        if not records:
            return True, [{"message": "검증할 기록이 없습니다"}]

        if end_index is None:
            end_index = len(records)

        results = []
        all_valid = True

        for i in range(start_index, end_index):
            record = records[i]
            record_id = record["record_id"]

            # 이전 체인 해시 확인
            if i == 0:
                expected_previous = self.GENESIS_HASH
            else:
                expected_previous = records[i - 1].get("chain_hash")

            stored_previous = record.get("previous_chain_hash")

            if stored_previous != expected_previous:
                results.append({
                    "index": i,
                    "record_id": record_id,
                    "status": "chain_broken",
                    "message": "체인이 끊어졌습니다 (이전 해시 불일치)",
                    "expected": expected_previous[:16] + "...",
                    "stored": stored_previous[:16] + "..."
                })
                all_valid = False
            else:
                results.append({
                    "index": i,
                    "record_id": record_id,
                    "status": "valid",
                    "message": "체인 연결 정상"
                })

        return all_valid, results

    def verify_all(self, limit: int = None, errors_only: bool = False) -> Dict:
        """
        전체 시스템 무결성 검증

        Args:
            limit: 검증할 최대 기록 수 (None이면 전체)
            errors_only: True이면 오류 기록만 검증

        Returns:
            검증 결과 보고서 (UI 호환 형식)
        """
        all_records = self.chain["records"]

        # 최근 기록부터 검증하도록 역순 처리
        records_to_verify = list(reversed(all_records))

        if limit:
            records_to_verify = records_to_verify[:limit]

        # 검증 결과 저장 (UI 호환 형식)
        report = {
            "verification_time": datetime.now().isoformat(),
            "summary": {
                "total_records": len(records_to_verify),
                "verified": 0,
                "failed": 0,
                "missing_files": 0,
                "chain_broken": 0
            },
            "records": []
        }

        # 1. 체인 연속성 검증
        chain_valid, chain_results = self.verify_chain()

        # 체인 끊김 개수 계산
        chain_broken_count = sum(1 for r in chain_results if r.get("status") == "chain_broken")
        report["summary"]["chain_broken"] = chain_broken_count

        # 2. 개별 기록 검증
        for record in records_to_verify:
            record_id = record["record_id"]
            valid, message, details = self.verify_record(record_id)

            # 기본 상태
            status = "verified" if valid else "failed"
            details_msg = message

            if valid:
                report["summary"]["verified"] += 1
            else:
                report["summary"]["failed"] += 1

                # 실패 유형 분류
                has_missing = False
                has_modified = False

                for file_check in details.get("file_checks", []):
                    if file_check.get("status") == "missing":
                        has_missing = True
                        report["summary"]["missing_files"] += 1
                    elif file_check.get("status") == "modified":
                        has_modified = True

                if has_missing:
                    status = "missing"
                    details_msg = "파일 누락"
                elif has_modified:
                    details_msg = "파일 변조 감지"

            # 체인 오류 확인
            chain_status = next(
                (r for r in chain_results if r.get("record_id") == record_id),
                None
            )
            if chain_status and chain_status.get("status") == "chain_broken":
                status = "chain_error"
                details_msg = "체인 연결 오류"

            # errors_only 모드에서는 오류 기록만 포함
            if errors_only and status == "verified":
                continue

            report["records"].append({
                "record_id": record_id,
                "person_name": record.get("person_name", "-"),
                "timestamp": record.get("timestamp", "-"),
                "status": status,
                "details": details_msg
            })

        return report

    def _generate_summary_message(self, report: Dict) -> str:
        """검증 결과 요약 메시지 생성"""
        total = report["total_records"]
        verified = report["verified_count"]
        failed = report["failed_count"]

        if failed == 0 and report["chain_valid"]:
            return f"전체 {total}개 기록 무결성 검증 통과"

        messages = []

        if not report["chain_valid"]:
            messages.append("해시 체인 연속성 오류 발견")

        if report["missing_count"] > 0:
            messages.append(f"누락된 파일: {report['missing_count']}개")

        if report["modified_count"] > 0:
            messages.append(f"변조된 파일: {report['modified_count']}개")

        return f"검증 실패 ({failed}/{total}건): " + ", ".join(messages)

    # =========================================================================
    # 반출 아카이브
    # =========================================================================

    def create_export_archive(self, start_date: str, end_date: str,
                              export_path: str, purpose: str = "",
                              exported_by: str = "") -> Dict:
        """
        기간별 반출 아카이브 생성

        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            export_path: 저장 경로 (ZIP 파일)
            purpose: 반출 목적
            exported_by: 반출자

        Returns:
            반출 결과 정보
        """
        # 해당 기간 기록 조회
        records = self.get_records_by_date(start_date, end_date)

        if not records:
            return {
                "success": False,
                "message": f"해당 기간({start_date} ~ {end_date})에 기록이 없습니다"
            }

        export_id = f"EXP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # ZIP 파일 생성
        try:
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 1. 기록 파일들 추가
                for record in records:
                    for file_type, file_info in record.get("files", {}).items():
                        filepath = file_info.get("path")
                        if filepath and os.path.exists(filepath):
                            arcname = f"records/{os.path.basename(filepath)}"
                            zf.write(filepath, arcname)

                # 2. 해시 체인 데이터 (해당 기간만)
                chain_export = {
                    "version": self.VERSION,
                    "export_period": {"start": start_date, "end": end_date},
                    "records": records
                }
                chain_json = json.dumps(chain_export, ensure_ascii=False, indent=2)
                zf.writestr("chain_verification/hash_chain_export.json", chain_json)

                # 3. 검증 결과 보고서
                verification_report = self._verify_records_for_export(records)
                report_json = json.dumps(verification_report, ensure_ascii=False, indent=2)
                zf.writestr("chain_verification/integrity_report.json", report_json)

                # 4. 반출 매니페스트
                manifest = {
                    "export_id": export_id,
                    "export_datetime": datetime.now().isoformat(),
                    "period": {"start": start_date, "end": end_date},
                    "total_records": len(records),
                    "exported_by": exported_by,
                    "purpose": purpose,
                    "software_version": "GARAMe Manager 1.9.7",
                    "hash_algorithm": self.HASH_ALGORITHM
                }
                manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
                zf.writestr("export_manifest.json", manifest_json)

                # 5. 독립 검증 도구 (Python 스크립트)
                verify_tool = self._generate_verification_tool()
                zf.writestr("chain_verification/verify_tool.py", verify_tool)

            # 6. 아카이브 해시 계산
            archive_hash = self.calculate_file_hash(export_path)

            # 7. 아카이브 해시 파일 생성 (별도 보관용)
            hash_file_path = export_path + ".hash"
            with open(hash_file_path, 'w', encoding='utf-8') as f:
                f.write(f"Export ID: {export_id}\n")
                f.write(f"Archive: {os.path.basename(export_path)}\n")
                f.write(f"Created: {datetime.now().isoformat()}\n")
                f.write(f"Period: {start_date} ~ {end_date}\n")
                f.write(f"Records: {len(records)}\n")
                f.write(f"Hash Algorithm: {self.HASH_ALGORITHM}\n")
                f.write(f"Archive Hash: {archive_hash}\n")

            # 8. 반출 이력 저장
            export_record = {
                "export_id": export_id,
                "export_datetime": datetime.now().isoformat(),
                "period": {"start": start_date, "end": end_date},
                "total_records": len(records),
                "archive_path": export_path,
                "archive_hash": archive_hash,
                "exported_by": exported_by,
                "purpose": purpose
            }
            self._add_export_history(export_record)

            return {
                "success": True,
                "export_id": export_id,
                "archive_path": export_path,
                "hash_file_path": hash_file_path,
                "archive_hash": archive_hash,
                "total_records": len(records),
                "period": {"start": start_date, "end": end_date},
                "message": f"{len(records)}개 기록 반출 완료"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"아카이브 생성 실패: {str(e)}"
            }

    # =========================================================================
    # 반출 이력 관리
    # =========================================================================

    def _add_export_history(self, export_record: Dict) -> None:
        """반출 이력 추가"""
        with self._lock:
            # export_history 필드가 없으면 생성
            if "export_history" not in self.chain:
                self.chain["export_history"] = []

            self.chain["export_history"].append(export_record)
            self._save_chain()

    def get_export_history(self) -> List[Dict]:
        """반출 이력 조회

        Returns:
            반출 이력 목록 (최신순)
        """
        history = self.chain.get("export_history", [])
        # 최신순 정렬
        return sorted(history, key=lambda x: x.get("export_datetime", ""), reverse=True)

    def get_export_by_id(self, export_id: str) -> Optional[Dict]:
        """반출 ID로 이력 조회

        Args:
            export_id: 반출 ID

        Returns:
            반출 이력 정보 또는 None
        """
        for record in self.chain.get("export_history", []):
            if record.get("export_id") == export_id:
                return record
        return None

    def delete_export_history(self, export_id: str) -> bool:
        """반출 이력 삭제

        Args:
            export_id: 반출 ID

        Returns:
            삭제 성공 여부
        """
        with self._lock:
            history = self.chain.get("export_history", [])
            original_count = len(history)
            self.chain["export_history"] = [
                r for r in history if r.get("export_id") != export_id
            ]
            if len(self.chain["export_history"]) < original_count:
                self._save_chain()
                return True
            return False

    def _verify_records_for_export(self, records: List[Dict]) -> Dict:
        """반출용 기록 검증"""
        report = {
            "verification_time": datetime.now().isoformat(),
            "total_records": len(records),
            "all_valid": True,
            "results": []
        }

        for record in records:
            valid, message, _ = self.verify_record(record["record_id"])
            report["results"].append({
                "record_id": record["record_id"],
                "valid": valid,
                "message": message
            })
            if not valid:
                report["all_valid"] = False

        return report

    def _generate_verification_tool(self) -> str:
        """독립 검증 도구 Python 스크립트 생성"""
        return '''#!/usr/bin/env python3
"""
안전교육 기록 독립 검증 도구
이 스크립트는 반출된 아카이브의 무결성을 검증합니다.
외부 의존성 없이 Python 표준 라이브러리만 사용합니다.
"""

import hashlib
import json
import os
import sys


def calculate_file_hash(filepath):
    """파일 SHA-256 해시 계산"""
    hash_obj = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def calculate_string_hash(text):
    """문자열 SHA-256 해시 계산"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def verify_chain(chain_file):
    """해시 체인 검증"""
    with open(chain_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = data.get("records", [])
    genesis_hash = "0" * 64

    print(f"\\n=== 해시 체인 검증 ===")
    print(f"총 기록 수: {len(records)}")

    all_valid = True
    for i, record in enumerate(records):
        record_id = record["record_id"]

        # 이전 해시 확인
        if i == 0:
            expected_previous = genesis_hash
        else:
            expected_previous = records[i - 1]["chain_hash"]

        if record["previous_chain_hash"] != expected_previous:
            print(f"[FAIL] {record_id}: 체인 연결 오류")
            all_valid = False
        else:
            print(f"[OK] {record_id}: 체인 연결 정상")

    return all_valid


def main():
    print("=" * 50)
    print("안전교육 기록 무결성 검증 도구")
    print("=" * 50)

    # 현재 디렉토리에서 체인 파일 찾기
    chain_file = "hash_chain_export.json"
    if not os.path.exists(chain_file):
        chain_file = "../chain_verification/hash_chain_export.json"

    if not os.path.exists(chain_file):
        print("오류: hash_chain_export.json 파일을 찾을 수 없습니다.")
        sys.exit(1)

    result = verify_chain(chain_file)

    print("\\n" + "=" * 50)
    if result:
        print("검증 결과: 통과 (PASS)")
    else:
        print("검증 결과: 실패 (FAIL)")
    print("=" * 50)

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
'''

    def verify_export_archive(self, archive_path: str) -> Tuple[bool, Dict]:
        """
        반출 아카이브 무결성 검증

        Args:
            archive_path: ZIP 파일 경로

        Returns:
            (성공여부, 검증결과)
        """
        result = {
            "archive_path": archive_path,
            "verification_time": datetime.now().isoformat(),
            "archive_exists": False,
            "archive_hash_valid": False,
            "chain_valid": False,
            "details": []
        }

        # 1. 아카이브 존재 확인
        if not os.path.exists(archive_path):
            result["message"] = "아카이브 파일이 존재하지 않습니다"
            return False, result

        result["archive_exists"] = True

        # 2. 해시 파일과 비교 (있는 경우)
        hash_file = archive_path + ".hash"
        if os.path.exists(hash_file):
            with open(hash_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.startswith("Archive Hash:"):
                        stored_hash = line.split(":")[-1].strip()
                        current_hash = self.calculate_file_hash(archive_path)

                        if stored_hash == current_hash:
                            result["archive_hash_valid"] = True
                            result["details"].append("아카이브 해시 일치")
                        else:
                            result["details"].append("아카이브 해시 불일치 - 파일 변조 의심")
                            result["message"] = "아카이브 파일이 변조되었습니다"
                            return False, result

        # 3. 내부 체인 데이터 검증
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                chain_data = json.loads(zf.read("chain_verification/hash_chain_export.json"))
                records = chain_data.get("records", [])

                # 체인 연속성 검증
                genesis_hash = "0" * 64
                for i, record in enumerate(records):
                    if i == 0:
                        expected_previous = genesis_hash
                    else:
                        expected_previous = records[i - 1]["chain_hash"]

                    if record["previous_chain_hash"] != expected_previous:
                        result["chain_valid"] = False
                        result["details"].append(f"기록 {record['record_id']}: 체인 연결 오류")
                    else:
                        result["details"].append(f"기록 {record['record_id']}: 체인 연결 정상")

                if all("정상" in d for d in result["details"] if "기록" in d):
                    result["chain_valid"] = True

        except Exception as e:
            result["message"] = f"아카이브 검증 실패: {str(e)}"
            return False, result

        success = result["archive_hash_valid"] and result["chain_valid"]
        result["message"] = "검증 통과" if success else "검증 실패"

        return success, result
