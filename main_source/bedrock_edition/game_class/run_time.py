import os,json,traceback,threading,functools,time
from .. import FileOperation,BaseNbtClass,DataSave,Constants
from typing import List,Dict,Union,Literal,Tuple

class dynamic_source :

    def __init__(self):
        minecraft_be_id_path = os.path.join("main_source", "update_source", "import_files")
        self.animation_controllers = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"animation_controller")))
        self.animations = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"animation")))
        self.blocks = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"block")))
        self.entities = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"entity")))
        self.fogs = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"fog")))
        self.items = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"item")))
        self.loot_tables = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"loot_table")))
        self.particles = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"particle")))
        self.sounds = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"sound")))
        self.musics = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"music")))
        self.tradings = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"trading")))
        self.recipes = json.loads(FileOperation.read_a_file(os.path.join(minecraft_be_id_path,"recipe")))

        self.dialogues = {}
        self.volumeareas = {}
        self.functions:Dict[str, Dict[Literal["crc32", "command"], Union[int, List[Tuple[str,functools.partial]] ]]] = {}
        self.camera_persets = {}

class runtime_variable :

    def __init__(self) -> None :
        from .. import Response
        self.scoreboard_score_remove:Dict[int,List[str]] = {}
        self.particle_alive:dict[int,List[List[float]]] = {}
        self.all_command_response:Dict[int,Dict[Literal["command","command_block","function"],
        Union[List[Response.Response_Template],List[Response.Response_Template],List[Response.Response_Template]]]] = {}

        self.command_block_schedules = []
        self.last_activated_pulse_cb = []

        self.terminal_command:str = ""
        self.terminal_send_command:bool = False
        self.terminal_command_feedback:List[Union[Tuple[int,str,int],Response.Response_Template]] = []

        self.how_times_run_all_command:int = -1 
        self.command_will_run:Dict[int,List[Tuple[str,functools.partial]]] = {}
        self.command_will_loop:List[Tuple[str,functools.partial]] = []
        self.command_will_run_test_end:List[Tuple[str,functools.partial]] = []
    
    def terminal_clear(self) :
        self.how_times_run_all_command = -1 
        self.command_will_run.clear()
        self.function_will_run.clear()
        self.command_will_loop.clear()
        self.function_will_loop.clear()
        self.command_will_run_test_end.clear()

        self.command_block_schedules.clear()
        self.last_activated_pulse_cb.clear()

        self.terminal_command_feedback.clear()
        self.particle_alive.clear()
        self.all_command_response.clear()

class minecraft_thread :

    def __init__(self) :
        from . import ExpandPackAPI

        self.loop_thread:threading.Thread = None

        self.world_name:str = None
        self.in_game_tag:bool = True
        self.game_load_over:bool = False

        self.infomation:dict = None
        self.minecraft_ident = dynamic_source()
        self.minecraft_world:BaseNbtClass.world_nbt = None
        self.minecraft_chunk:BaseNbtClass.chunk_nbt = None
        self.minecraft_scoreboard:BaseNbtClass.scoreboard_nbt = None

        self.game_version = (1, 20, 60)
        self.runtime_variable = runtime_variable()

        #visualization_API
        self.visualization_object:ExpandPackAPI.visualization = None

    def register_response(self, response_type:Literal["delay_command","loop_command","command_block","delay_function","loop_function",
                          "end_command"], command:str, response) :
        now_time = self.minecraft_world.game_time
        if now_time not in self.runtime_variable.all_command_response : 
            self.runtime_variable.all_command_response[now_time] = {
                "delay_command":[],"loop_command":[],"command_block":[],"delay_function":[],"loop_function":[],"end_command":[]}
        self.runtime_variable.all_command_response[now_time][response_type].append(response.set_command(command))

    def __game_loading__(self, word_name:str) :
        from . import ExpandPackAPI,JoinWorld

        self.world_name:str = word_name
        try :
            self.world_infomation = json.loads(FileOperation.read_a_file(os.path.join('save_world',word_name,'level_name')))
            self.minecraft_world = json.loads(FileOperation.read_a_file(os.path.join('save_world',word_name,'world_info')),object_hook=DataSave.decoding)
            self.minecraft_scoreboard = json.loads(FileOperation.read_a_file(os.path.join('save_world',word_name,'scoreboard')),object_hook=DataSave.decoding)
            self.minecraft_chunk = json.loads(FileOperation.read_a_file(os.path.join('save_world',word_name,'chunk_data')),object_hook=DataSave.decoding)
        except :
            traceback.print_exc(file=open(os.path.join("log", "join_world.txt")))
            raise Exception("启动世界失败\n日志join_world.txt已保存\n尝试咨询开发者解决问题")

        os.makedirs(os.path.join("save_world", self.world_name, "resource_packs"),exist_ok=True)
        os.makedirs(os.path.join("save_world", self.world_name, "behavior_packs"),exist_ok=True)
        os.makedirs(os.path.join("save_world", self.world_name, "command_blocks"),exist_ok=True)
        for dis in Constants.DIMENSION_INFO : os.makedirs(os.path.join("save_world", self.world_name, "chunk_info", dis),exist_ok=True)

        for id_regs in Constants.IDENTIFIER_TRANSFORM['block']['id_register'] : self.minecraft_ident.blocks[id_regs] = {}

        if ("verification_challenge" not in self.world_infomation) or (not self.world_infomation['verification_challenge']) :  
            self.visualization_object = ExpandPackAPI.visualization(self)
            a = JoinWorld.join_game_load(self)
            if a : 
                with open(os.path.join("log", "join_world.txt"),"w+",encoding="utf-8") as f : f.write("\n".join(a))
                result = "加入世界成功,有文件加载失败\n日志join_world.txt已保存\n游戏版本：%s.%s.%s" % (1,20,50)
            else : result = "加入世界成功\n游戏版本：%s.%s.%s" % (1,20,50)
        else : 
            self.verification_challenge_object = ExpandPackAPI.challenge(self)
            JoinWorld.join_game_load(self)
            result = "你已进入每周挑战世界\n本世界无法进行交互\n可以自行删除这个世界"

        self.loop_thread = threading.Thread(target=self.__game_looping__)
        return result
        
    def __game_looping__(self) :
        from . import GameLoop
        try :
            while self.in_game_tag :
                time.sleep(0.25)
                for func in GameLoop.loop_function_list : 
                    if not self.in_game_tag : return None
                    func(self)
        except : traceback.print_exc(file=open(os.path.join("log","game_run.txt"), "w+",encoding="utf-8"))

    def __exit_world__(self) :
        self.in_game_tag = False
        if not self.game_load_over : return "不保存退出世界成功"
        while self.loop_thread and self.loop_thread.is_alive() : time.sleep(0.25)
        try :
            self.minecraft_chunk.____save_and_write_db_file____(self.world_name)

            save_file = os.path.join("save_world", self.world_name, "level_name")
            json1 = json.dumps(self.world_infomation)
            FileOperation.write_a_file(save_file, json1)

            save_file = os.path.join("save_world", self.world_name, "world_info")
            json1 = json.dumps(self.minecraft_world.__save__(), default=DataSave.encoding)
            FileOperation.write_a_file(save_file, json1)
            
            save_file = os.path.join("save_world", self.world_name, "scoreboard")
            json1 = json.dumps(self.minecraft_scoreboard.__save__(), default=DataSave.encoding)
            FileOperation.write_a_file(save_file, json1)
            
            save_file = os.path.join("save_world", self.world_name, "chunk")
            json1 = json.dumps(self.minecraft_chunk.__save__(), default=DataSave.encoding)
            FileOperation.write_a_file(save_file, json1)

            return "退出世界成功"
        except : 
            traceback.print_exc(file=open(os.path.join("log","save_world.txt"), "w", encoding="utf-8"))
            return "世界保存出错\n日志save_world.txt已保存\n请联系开发者解决"

