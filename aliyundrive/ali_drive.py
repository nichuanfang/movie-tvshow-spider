from aligo import Aligo
from aligo.types.Enum import CheckNameMode
from aligo.types.BaseFile import BaseFile
from aligo.response.CreateFileResponse import CreateFileResponse
from aligo.request import MoveFileRequest
from aligo.response import MoveFileResponse
from aligo.response import MoveFileToTrashResponse
import subprocess

class Alidrive():
    
    def __init__(self,aligo:Aligo):
        self.aligo = aligo

    def get_file_by_path(self,path: str = '/', parent_file_id: str = 'root',
                            check_name_mode: CheckNameMode = 'refuse',
                            drive_id: str = None): # type: ignore
        """根据路径获取云盘文件对象, 先找到啥就返回啥（早期可能存在同名文件（夹）），否则返回None

        Args:
            path: [str] 路径，无需以'/'开头
            parent_file_id: Optional[str] 父文件夹ID，默认为根目录，意思是基于根目录查找
            check_name_mode: Optional[CheckNameMode] 检查名称模式，默认为 'refuse'
            drive_id: Optional[str] 存储桶ID

        Returns:
            [BaseFile] 文件对象，或 None
        """    
        return self.aligo.get_file_by_path(path,parent_file_id,check_name_mode,drive_id)

    def get_folder_by_path( self,path: str = '/', parent_file_id: str = 'root', create_folder: bool = False,
                check_name_mode: CheckNameMode = 'refuse', drive_id: str = None) -> BaseFile | CreateFileResponse | None: # type: ignore
        """根据文件路径，获取网盘文件对象

        Args:
            path: [str] 完整路径，无需以 '/' 开始或结束
            parent_file_id: Optional[str] 父文件夹ID，默认为根目录，意思是基于根目录查找
            create_folder:  Optional[bool] 不存在是否创建，默认：True. 此行为效率最高
            check_name_mode: Optional[CheckNameMode] 检查名称模式，默认为 'refuse'
            drive_id: Optional[str] 存储桶ID，一般情况下，drive_id 参数都无需提供

        Returns:
            文件对象，或创建文件夹返回的对象，或 None
        """    
        return self.aligo.get_folder_by_path(path,parent_file_id,create_folder,check_name_mode,drive_id)

    def get_file(self,file_id: str, drive_id: str = None): # type: ignore
        """获取文件/文件夹

        Args:
            file_id: [str] 文件ID
            drive_id: Optional[str] 存储桶ID
        
        Returns:
            [BaseFile] 文件对象
        """    
        return self.aligo.get_file(file_id)    

    def get_file_list(self,parent_file_id:str = 'root',drive_id: str = None, **kwargs): # type: ignore
        """获取文件列表

        Args:
            parent_file_id: Optional[str] 文件夹ID，默认为根目录
            drive_id: Optional[str] 存储桶ID
            kwargs: [dict] 其他参数

        Returns:
            [List[BaseFile]] 文件列表
        """    
        return self.aligo.get_file_list(parent_file_id,drive_id,**kwargs)



    def move(self,file_id: str = None, # type: ignore
                    to_parent_file_id: str = 'root',
                    new_name: str = None, # type: ignore
                    drive_id: str = None, # type: ignore
                    to_drive_id: str = None, # type: ignore
                    **kwargs):
        """移动文件/文件夹

        Args:
            file_id: [必选] 文件/文件夹ID
            to_parent_file_id: [可选] 目标文件夹ID 默认移动到 根目录
            new_name: [可选] 新文件名
            drive_id: [可选] 文件所在的网盘ID
            to_drive_id: [可选] 目标网盘ID
            kwargs: [可选] 其他参数
        Returns: 
            [MoveFileResponse]
        """  
        return self.aligo.move_file(file_id,to_parent_file_id,new_name,drive_id,to_drive_id,**kwargs)

    def move_to_trash(self,file_id: str, drive_id: str = None) -> MoveFileToTrashResponse: # type: ignore
        """移动文件到回收站

        Args:
            file_id: [必须] 文件ID
            drive_id: [可选] 文件所在的网盘ID

        Returns:
            [MoveFileToTrashResponse]
        """    
        return self.aligo.move_file_to_trash(file_id,drive_id)


    def rename(self,file_id: str,
                        name: str,
                        check_name_mode: CheckNameMode = 'refuse',
                        drive_id: str = None): # type: ignore
        """文件/文件夹重命名

        Args:
            file_id: [必选] 文件id
            name: [必选] 新的文件名
            check_name_mode: [可选] 检查文件名模式
            drive_id: [可选] 文件所在的网盘id

        Returns:
            _type_: [BaseFile] 文件信息
        """    
        return self.aligo.rename_file(file_id,name,check_name_mode,drive_id)
    
    # 指定时间后移除已刮削好的电影/剧集
    def tmm_movie_check(self):
        tmm_movies_folder = self.get_folder_by_path('tmm/tmm-movies')
        assert tmm_movies_folder is not None
        def callable(path:str,file:BaseFile):
            # 获取.mkv文件 
            if file.file_extension.lower() in ['mkv','mov','wmv','flv','avi','avchd','webm','mp4']:
                # 查看当前文件夹下是否有同名文件 
                flag = False
                for item in self.get_file_list(file.parent_file_id):
                    if item.file_extension.lower() == 'nfo':
                        flag = True
                        break
                if flag:
                    # 有nfo文件 直接将该电影文件夹移至movies文件夹
                    self.move_to_movies(file.parent_file_id,tmm_movies_folder.file_id,[])
            return None

        self.aligo.walk_files(callable,tmm_movies_folder.file_id)

    def move_to_movies(self,parent_file_id:str,tmm_file_id:str,path_list:list):
        """递归文件夹 在movies创建电影文件夹

        Args:
            parent_file_id (str): 父文件id
            tmm_file_id (str): tmm文件夹id
            path_list (list): 路径列表
        """    
        if parent_file_id != tmm_file_id:
            file = self.get_file(parent_file_id)
            # 操作 
            path_list.append(file.name)
            self.move_to_movies(file.parent_file_id,tmm_file_id,path_list)
        else:
            # 分层级在movies中创建文件夹
            path_list.reverse()
            file_path = 'tmm/tmm-movies/'+'/'.join(path_list)
            base_path = 'movies'
            final_path = base_path
            final_path_dp = []
            for path in path_list:
                # 如果是最后一个元素 则移动第一个文件夹到final_path
                if path == path_list[-1]:
                    src_file: BaseFile | CreateFileResponse | None = self.get_folder_by_path(file_path)
                    assert src_file is not None
                    desc_file = self.get_folder_by_path(final_path)
                    assert desc_file is not None
                    # 如果final_path下面存在同名文件夹则覆盖
                    desc_file_list = self.get_file_list(desc_file.file_id)
                    if len(desc_file_list)!=0:
                        for desc_file_item in desc_file_list:
                            if not isinstance(src_file,CreateFileResponse)  and desc_file_item.name == src_file.name:
                                self.move_to_trash(desc_file_item.file_id)
                            pass
                    self.move(src_file.file_id,desc_file.file_id)
                    # 移除final_path_dp的空文件夹
                    for dp in final_path_dp:
                        dp_file = self.get_folder_by_path(dp)
                        if dp_file is not None:
                            file_list = self.get_file_list(dp_file.file_id)
                            if len(file_list) == 0:
                                # 移除该文件夹
                                self.move_to_trash(dp_file.file_id)
                        pass
                final_path+='/'+path
                final_path_dp.append(final_path.replace('movies', 'tmm/tmm-movies'))
                self.get_folder_by_path(final_path,create_folder=True)


if __name__ == '__main__':
    # hosts =  get_file_by_path('hosts.txt')
    # folder = get_folder_by_path('movieset') 
    # assert hosts is not None
    # assert folder is not None
    # res:MoveFileResponse = move_file(file.file_id,folder.file_id)
    # move(test_folder.file_id,folder.file_id)
    # move_to_trash(test_folder.file_id)
    # rename(hosts.file_id,'ssd.txt')
    pass