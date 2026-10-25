import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_KEY_PATH, GDRIVE_TARGET_FOLDER_ID

def get_drive_service():
    scope = [
        "https://www.googleapis.com/auth/drive",
        "https://spreadsheets.google.com/feeds"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_PATH, scope)
    return build("drive", "v3", credentials=creds)

def check_drive_folder_access(folder_id: str = GDRIVE_TARGET_FOLDER_ID):
    """지정된 구글 드라이브 폴더에 서비스 계정이 접근 가능한지 확인"""
    service = get_drive_service()
    try:
        folder = service.files().get(
            fileId=folder_id,
            fields="id, name, mimeType, capabilities"
        ).execute()
        return {
            "success": True,
            "folder_name": folder.get("name"),
            "can_add_children": folder.get("capabilities", {}).get("canAddChildren", False)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "hint": "구글 드라이브 폴더에 서비스 계정(adot-workflow@adot-workflow.iam.gserviceaccount.com)을 '편집자(Editor)'로 공유해주세요."
        }

def upload_video_to_gdrive(local_file_path: str, custom_filename: str = None, folder_id: str = GDRIVE_TARGET_FOLDER_ID):
    """
    로컬 MP4 동영상 파일을 구글 드라이브 지정 폴더에 업로드합니다.
    """
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"업로드할 동영상 파일이 존재하지 않습니다: {local_file_path}")

    filename = custom_filename or os.path.basename(local_file_path)
    service = get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    media = MediaFileUpload(
        local_file_path,
        mimetype="video/mp4",
        resumable=True
    )

    try:
        print(f"[Google Drive] 업로드 시작: {filename} -> 폴더 ID: {folder_id}")
        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink"
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[Google Drive] 업로드 진행률: {int(status.progress() * 100)}%")

        print(f"[Google Drive] 업로드 완료! File ID: {response.get('id')}")
        
        # 누구나 보기 가능하도록 권한 설정 (옵션)
        try:
            service.permissions().create(
                fileId=response.get("id"),
                body={"role": "reader", "type": "anyone"},
                fields="id"
            ).execute()
        except Exception:
            pass

        return {
            "success": True,
            "file_id": response.get("id"),
            "file_name": response.get("name"),
            "view_link": response.get("webViewLink"),
            "download_link": response.get("webContentLink")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "hint": "구글 드라이브 폴더에 서비스 계정(adot-workflow@adot-workflow.iam.gserviceaccount.com)을 '편집자'로 공유해주시면 즉시 자동 업로드됩니다."
        }

if __name__ == "__main__":
    print("Checking Google Drive Folder access...")
    res = check_drive_folder_access()
    print("Result:", res)
