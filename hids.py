from flask_restful import Resource, reqparse
from models.computer import ComputerModel
from models.user import UserModel
from models.file import FileModel
from settings import FILE_DELETION_TIMEOUT, ANALYZER_URL
import time
import requests


class Hids(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)

    parser.add_argument('uuid',
                        type=str,
                        required=False,
                        help="Every file- needs a guid!"
                        )
    parser.add_argument('computer',
                        type=str,
                        required=False,
                        help="Every file- needs a computer!"
                        )
    parser.add_argument('files',
                        type=list,
                        required=False,
                        location='json',
                        help="Every file- needs a file!"
                        )

    def post(self):
        data = Hids.parser.parse_args()
        uuid = data["uuid"]
        pc_name = data["computer"]

        # hier maak ik een log aan voor de analyser

        # return {"message": "A file with that name already exists"}

        # create user if not exist
        if UserModel.find_by_uuid(uuid) is None:
            UserModel(uuid).save_to_db()

        # create pc_name if not exist
        if ComputerModel.find_by_name(pc_name, uuid) is None:
            ComputerModel(pc_name, uuid).save_to_db()

        pc_id = ComputerModel.find_by_name(pc_name, uuid).json()["id"]
        # add files to user/pc
        for file in data["files"]:
            file_path = file["path"]
            file_name = file["name"]
            file_hash = file["hash"]
            file_id = FileModel.find_existing(file_path, file_name, pc_id)
            if file_id is None:
                FileModel(file, pc_id).save_to_db()
            else:
                file_id = file_id.json()["id"]
                FileModel.find_and_replace(file_id, file_hash)

        # changed_files = FileModel.find_changes_by_pc_id(pc_id).json()
        # changed_files = {'files': [file.json() for file in FileModel.find_changes_by_pc_id(pc_id)]}
        # print(changed_files)
        analyzer_object = {}
        for file in FileModel.find_by_pc_id(pc_id):
            file = file.json()
            if file["prev_hash"] is None:
                analyzer_object.update({"new": file})
            elif file["curr_hash"] != file["prev_hash"]:
                analyzer_object.update({"update": file})
            elif (time.time() - file["last_updated"]) > FILE_DELETION_TIMEOUT:
                analyzer_object.update({"deleted": file})
        print(analyzer_object)
        try:
            response = requests.post(url=ANALYZER_URL, json=analyzer_object)
        except:
            pass
        return {"message": "file created successfully"}, 201


class ComputerList(Resource):
    def get(self):
        return {'computers': [computer.json() for computer in ComputerModel.query.all()]}


class FileList(Resource):
    def get(self):
        return {'files': [file.json() for file in FileModel.query.all()]}
