import asyncio
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from myUtils.auth import check_cookie
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from conf import BASE_DIR
from myUtils.login import get_tencent_cookie, douyin_cookie_gen, get_ks_cookie, xiaohongshu_cookie_gen
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs

active_queues = {}
app = Flask(__name__)

#允许所有来源跨域访问
CORS(app)

# 限制上传文件大小为160MB
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

# 获取当前目录（假设 index.html 和 assets 在这里）
current_dir = os.path.dirname(os.path.abspath(__file__))

# 处理所有静态资源请求（未来打包用）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（未来打包用）
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

@app.route('/vite.svg')
def vite_svg():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

# （未来打包用）
@app.route('/')
def index():  # put application's code here
    return send_from_directory(current_dir, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        # 保存文件到指定位置
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{file.filename}")
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": f"{uuid_v1}_{file.filename}"}), 200
    except Exception as e:
        return jsonify({"code":500,"msg": str(e),"data":None}), 500

@app.route('/getFile', methods=['GET'])
def get_file():
    # 获取 filename 参数
    filename = request.args.get('filename')

    if not filename:
        return jsonify({"code": 400, "msg": "filename is required", "data": None}), 400

    # 防止路径穿越攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({"code": 400, "msg": "Invalid filename", "data": None}), 400

    # 拼接完整路径
    file_path = str(Path(BASE_DIR / "videoFile"))

    # 返回文件
    return send_from_directory(file_path,filename)


@app.route('/uploadSave', methods=['POST'])
def upload_save():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400

    # 获取表单中的自定义文件名（可选）
    custom_filename = request.form.get('filename', None)
    if custom_filename:
        filename = custom_filename + "." + file.filename.split('.')[-1]
    else:
        filename = file.filename

    try:
        # 生成 UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # 构造文件名和路径
        final_filename = f"{uuid_v1}_{filename}"
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{filename}")

        # 保存文件
        file.save(filepath)

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path)
            VALUES (?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename))
            conn.commit()
            print("✅ 上传文件已记录")

        return jsonify({
            "code": 200,
            "msg": "File uploaded and saved successfully",
            "data": {
                "filename": filename,
                "filepath": final_filename
            }
        }), 200

    except Exception as e:
        print(f"Upload failed: {e}")
        return jsonify({
            "code": 500,
            "msg": f"upload failed: {e}",
            "data": None
        }), 500

@app.route('/getFiles', methods=['GET'])
def get_all_files():
    try:
        # 使用 with 自动管理数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
            cursor = conn.cursor()

            # 查询所有记录
            cursor.execute("SELECT * FROM file_records")
            rows = cursor.fetchall()

            # 将结果转为字典列表，并提取UUID
            data = []
            for row in rows:
                row_dict = dict(row)
                # 从 file_path 中提取 UUID (文件名的第一部分，下划线前)
                if row_dict.get('file_path'):
                    file_path_parts = row_dict['file_path'].split('_', 1)  # 只分割第一个下划线
                    if len(file_path_parts) > 0:
                        row_dict['uuid'] = file_path_parts[0]  # UUID 部分
                    else:
                        row_dict['uuid'] = ''
                else:
                    row_dict['uuid'] = ''
                data.append(row_dict)

            return jsonify({
                "code": 200,
                "msg": "success",
                "data": data
            }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("get file failed!"),
            "data": None
        }), 500


@app.route("/getAccounts", methods=['GET'])
def getAccounts():
    """快速获取所有账号信息，不进行cookie验证"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM user_info''')
            rows = cursor.fetchall()
            rows_list = [list(row) for row in rows]

            print("\n📋 当前数据表内容（快速获取）：")
            for row in rows:
                print(row)

            return jsonify(
                {
                    "code": 200,
                    "msg": None,
                    "data": rows_list
                }), 200
    except Exception as e:
        print(f"获取账号列表时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"获取账号列表失败: {str(e)}",
            "data": None
        }), 500


@app.route("/getValidAccounts",methods=['GET'])
async def getValidAccounts():
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM user_info''')
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        print("\n📋 当前数据表内容：")
        for row in rows:
            print(row)
        for row in rows_list:
            flag = await check_cookie(row[1],row[2])
            if not flag:
                row[4] = 0
                cursor.execute('''
                UPDATE user_info 
                SET status = ? 
                WHERE id = ?
                ''', (0,row[0]))
                conn.commit()
                print("✅ 用户状态已更新")
        for row in rows:
            print(row)
        return jsonify(
                        {
                            "code": 200,
                            "msg": None,
                            "data": rows_list
                        }),200

@app.route('/deleteFile', methods=['GET'])
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # 获取文件路径并删除实际文件
            file_path = Path(BASE_DIR / "videoFile" / record['file_path'])
            if file_path.exists():
                try:
                    file_path.unlink()  # 删除文件
                    print(f"✅ 实际文件已删除: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除实际文件失败: {e}")
                    # 即使删除文件失败，也要继续删除数据库记录，避免数据不一致
            else:
                print(f"⚠️ 实际文件不存在: {file_path}")

            # 删除数据库记录
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/deleteAccount', methods=['GET'])
def delete_account():
    account_id = request.args.get('id')

    if not account_id or not account_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing account ID",
            "data": None
        }), 400

    account_id = int(account_id)

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除关联的cookie文件
            if record.get('filePath'):
                cookie_file_path = Path(BASE_DIR / "cookiesFile" / record['filePath'])
                if cookie_file_path.exists():
                    try:
                        cookie_file_path.unlink()
                        print(f"✅ Cookie文件已删除: {cookie_file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除Cookie文件失败: {e}")

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"delete failed: {str(e)}",
            "data": None
        }), 500


# SSE 登录接口
@app.route('/login')
def login():
    # 1 小红书 2 视频号 3 抖音 4 快手
    type = request.args.get('type')
    # 账号名
    id = request.args.get('id')

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    active_queues[id] = status_queue

    def on_close():
        print(f"清理队列: {id}")
        del active_queues[id]
    # 启动异步任务线程
    thread = threading.Thread(target=run_async_function, args=(type,id,status_queue), daemon=True)
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 关键：禁用 Nginx 缓冲
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/postVideo', methods=['POST'])
def postVideo():
    # 获取JSON数据
    data = request.get_json()

    if not data:
        return jsonify({"code": 400, "msg": "请求数据不能为空", "data": None}), 400

    # 从JSON数据中提取fileList和accountList
    file_list = data.get('fileList', [])
    account_list = data.get('accountList', [])
    type = data.get('type')
    title = data.get('title')
    tags = data.get('tags')
    category = data.get('category')
    enableTimer = data.get('enableTimer')
    if category == 0:
        category = None
    productLink = data.get('productLink', '')
    productTitle = data.get('productTitle', '')
    thumbnail_path = data.get('thumbnail', '')
    is_draft = data.get('isDraft', False)  # 新增参数：是否保存为草稿

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')

    # 参数校验
    if not file_list:
        return jsonify({"code": 400, "msg": "文件列表不能为空", "data": None}), 400
    if not account_list:
        return jsonify({"code": 400, "msg": "账号列表不能为空", "data": None}), 400
    if not type:
        return jsonify({"code": 400, "msg": "平台类型不能为空", "data": None}), 400
    if not title:
        return jsonify({"code": 400, "msg": "标题不能为空", "data": None}), 400

    # 打印获取到的数据（仅作为示例）
    print("File List:", file_list)
    print("Account List:", account_list)

    try:
        match type:
            case 1:
                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, thumbnail_path)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft, thumbnail_path)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, thumbnail_path, productLink, productTitle)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, thumbnail_path)
            case _:
                return jsonify({"code": 400, "msg": f"不支持的平台类型: {type}", "data": None}), 400

        # 返回响应给客户端
        return jsonify(
            {
                "code": 200,
                "msg": "发布任务已提交",
                "data": None
            }), 200
    except Exception as e:
        print(f"发布视频时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"发布失败: {str(e)}",
            "data": None
        }), 500


@app.route('/updateUserinfo', methods=['POST'])
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500

@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"code": 400, "msg": "Expected a JSON array", "data": None}), 400
    for data in data_list:
        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None
        productLink = data.get('productLink', '')
        productTitle = data.get('productTitle', '')
        is_draft = data.get('isDraft', False)

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        # 打印获取到的数据（仅作为示例）
        print("File List:", file_list)
        print("Account List:", account_list)
        match type:
            case 1:
                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                               start_days)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, productLink, productTitle)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

# Cookie文件上传API
@app.route('/uploadCookie', methods=['POST'])
def upload_cookie():
    try:
        if 'file' not in request.files:
            return jsonify({
                "code": 400,
                "msg": "没有找到Cookie文件",
                "data": None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "code": 400,
                "msg": "Cookie文件名不能为空",
                "data": None
            }), 400

        if not file.filename.endswith('.json'):
            return jsonify({
                "code": 400,
                "msg": "Cookie文件必须是JSON格式",
                "data": None
            }), 400

        # 获取账号信息
        account_id = request.form.get('id')
        platform = request.form.get('platform')

        if not account_id or not platform:
            return jsonify({
                "code": 400,
                "msg": "缺少账号ID或平台信息",
                "data": None
            }), 400

        # 从数据库获取账号的文件路径
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT filePath FROM user_info WHERE id = ?', (account_id,))
            result = cursor.fetchone()

        if not result:
            return jsonify({
                "code": 500,
                "msg": "账号不存在",
                "data": None
            }), 404

        # 保存上传的Cookie文件到对应路径
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / result['filePath'])
        cookie_file_path.parent.mkdir(parents=True, exist_ok=True)

        file.save(str(cookie_file_path))

        # 更新数据库中的账号信息（可选，比如更新更新时间）
        # 这里可以根据需要添加额外的处理逻辑

        return jsonify({
            "code": 200,
            "msg": "Cookie文件上传成功",
            "data": None
        }), 200

    except Exception as e:
        print(f"上传Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"上传Cookie文件失败: {str(e)}",
            "data": None
        }), 500


# Cookie文件下载API
@app.route('/downloadCookie', methods=['GET'])
def download_cookie():
    try:
        file_path = request.args.get('filePath')
        if not file_path:
            return jsonify({
                "code": 500,
                "msg": "缺少文件路径参数",
                "data": None
            }), 400

        # 验证文件路径的安全性，防止路径遍历攻击
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / file_path).resolve()
        base_path = Path(BASE_DIR / "cookiesFile").resolve()

        if not cookie_file_path.is_relative_to(base_path):
            return jsonify({
                "code": 500,
                "msg": "非法文件路径",
                "data": None
            }), 400

        if not cookie_file_path.exists():
            return jsonify({
                "code": 500,
                "msg": "Cookie文件不存在",
                "data": None
            }), 404

        # 返回文件
        return send_from_directory(
            directory=str(cookie_file_path.parent),
            path=cookie_file_path.name,
            as_attachment=True
        )

    except Exception as e:
        print(f"下载Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"下载Cookie文件失败: {str(e)}",
            "data": None
        }), 500


# 包装函数：在线程中运行异步函数
def run_async_function(type,id,status_queue):
    match type:
        case '1':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue))
            loop.close()
        case '2':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_tencent_cookie(id,status_queue))
            loop.close()
        case '3':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(douyin_cookie_gen(id,status_queue))
            loop.close()
        case '4':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_ks_cookie(id,status_queue))
            loop.close()

# SSE 流生成器函数
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
        else:
            # 避免 CPU 占满
            time.sleep(0.1)

# ========== AI 创作者中心 ==========

@app.route('/api/ai/generate', methods=['POST'])
def ai_generate():
    """根据素材类型生成提示词、标题、话题建议"""
    import subprocess, json, tempfile, os, base64, requests as http_req
    from myUtils.auth import check_cookie

    data = request.get_json()
    material_type = data.get('type')   # url | image | text | video
    content = data.get('content', '')  # URL 或文本内容
    platform = data.get('platform', 'douyin')  # douyin | xiaohongshu

    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业的短视频内容策划师，擅长根据素材为抖音/小红书平台生成爆款内容方案。
请根据用户提供的素材，分析并生成以下内容（严格使用中文输出）：

1. **视频提示词（Video Prompt）**
   - 用于 AI 生成视频的核心描述词，50-150字
   - 风格、氛围、画面重点、运镜方式

2. **标题建议**
   - 5个爆款标题选项（带序号）
   - 每个标题控制在20字以内
   - 带话题标签格式如：#话题

3. **话题建议**
   - 10个相关话题标签
   - 格式：#话题名

4. **内容分析**
   - 素材的核心卖点（50字内）
   - 适合的受众群体
   - 最佳发布时段建议

输出格式（严格按此格式，不要添加额外说明）：
```
[PROMPT]
（视频提示词内容）
[/PROMPT]

[TITLES]
1. 标题1
2. 标题2
3. 标题3
4. 标题4
5. 标题5
[/TITLES]

[TOPICS]
#话题1 #话题2 #话题3 #话题4 #话题5 #话题6 #话题7 #话题8 #话题9 #话题10
[/TOPICS]

[ANALYSIS]
卖点：（50字内）
受众：（30字内）
时段：（20字内）
[/ANALYSIS]
```"""

    try:
        # 1. 图片/视频：先下载并转 base64
        if material_type == 'image' and content.startswith('data:'):
            # 前端传来的 base64
            b64_data = content.split(',')[1]
            user_prompt = f"[用户上传了图片素材]\n请分析这张图片，生成内容方案。"
            payload = json.dumps([{"role": "user", "content": user_prompt, "image_urls": [f"data:image/jpeg;base64,{b64_data}"]}])
        elif material_type == 'image' and content.startswith('http'):
            user_prompt = f"[用户提供了图片链接：{content}]\n请分析这张图片，生成内容方案。"
            payload = json.dumps([{"role": "user", "content": user_prompt}])
        elif material_type == 'video' and content.startswith('data:'):
            # 视频 base64（偏大，一般不推荐）
            user_prompt = "[用户上传了视频素材]\n请分析这个视频内容，生成内容方案。"
            payload = json.dumps([{"role": "user", "content": user_prompt}])
        elif material_type == 'video' and content.startswith('http'):
            user_prompt = f"[用户提供了视频链接：{content}]\n请分析这个视频内容，生成内容方案。"
            payload = json.dumps([{"role": "user", "content": user_prompt}])
        elif material_type == 'url':
            user_prompt = f"[用户提供了素材链接：{content}]\n请分析这个链接的内容，生成内容方案。"
            payload = json.dumps([{"role": "user", "content": user_prompt}])
        elif material_type == 'text':
            user_prompt = f"[用户提供了文本素材：\n{content}]\n请分析这段文本，生成内容方案。"
            payload = json.dumps([{"role": "user", "content": user_prompt}])
        else:
            return jsonify({"error": "不支持的素材类型或内容为空"}), 400

        full_payload = json.dumps([{"role": "system", "content": SYSTEM_PROMPT}])
        import copy
        messages = json.loads(full_payload)
        user_msgs = json.loads(payload)
        messages.extend(user_msgs)

        # 读取 MiniMax API Key
        config_path = os.path.expanduser("~/.mmx/config.json")
        api_key = None
        if os.path.exists(config_path):
            with open(config_path) as f:
                cfg = json.load(f)
                api_key = cfg.get("api_key")

        if not api_key:
            return jsonify({"error": "未配置 MiniMax API Key，请联系管理员"}), 500

        # 调用 MiniMax 文本 API
        req = http_req.post(
            "https://api.minimaxi.com/v1/text/chatcompletion_v2",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "MiniMax-M2.7",
                "messages": messages,
                "max_tokens": 1500,
                "temperature": 0.7
            },
            timeout=60
        )
        result = req.json()
        if req.status_code != 200:
            return jsonify({"error": f"MiniMax API 错误: {result.get('error', {}).get('message', str(result))}"}), 502

        reply = result["choices"][0]["message"]["content"]
        return jsonify({"success": True, "content": reply})

    except http_req.exceptions.Timeout:
        return jsonify({"error": "AI 生成超时，请重试"}), 504
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"生成失败: {str(e)}"}), 500


# ========== 发布记录 & 草稿 ==========

@app.route('/getPublishRecords', methods=['GET'])
def get_publish_records():
    """获取发布记录，支持筛选和分页"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        platform = request.args.get('platform', '')
        status = request.args.get('status', '')
        keyword = request.args.get('keyword', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # WHERE 条件
        conditions = []
        params = []
        if platform:
            conditions.append('platform = ?')
            params.append(platform)
        if status:
            conditions.append('status = ?')
            params.append(status)
        if keyword:
            conditions.append('title LIKE ?')
            params.append(f'%{keyword}%')
        if start_date:
            conditions.append('date(created_at) >= ?')
            params.append(start_date)
        if end_date:
            conditions.append('date(created_at) <= ?')
            params.append(end_date)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        # 总数
        cur.execute(f'SELECT COUNT(*) as cnt FROM publish_records WHERE {where_clause}', params)
        total = cur.fetchone()['cnt']

        # 成功/失败数
        cur.execute(f'SELECT status, COUNT(*) as cnt FROM publish_records WHERE {where_clause} GROUP BY status', params)
        stat_rows = cur.fetchall()
        success_count = sum(r['cnt'] for r in stat_rows if r['status'] == 1)
        fail_count = sum(r['cnt'] for r in stat_rows if r['status'] == 2)

        # 分页数据
        offset = (page - 1) * page_size
        cur.execute(
            f'SELECT * FROM publish_records WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?',
            [*params, page_size, offset]
        )
        rows = cur.fetchall()
        conn.close()

        records = [dict(row) for row in rows]
        return jsonify({
            'code': 200, 'data': records, 'total': total,
            'success_count': success_count, 'fail_count': fail_count
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'code': 500, 'msg': str(e)}), 500

@app.route('/deletePublishRecord', methods=['DELETE'])
def delete_publish_record():
    """删除单条发布记录"""
    try:
        rid = request.args.get('id')
        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        cur = conn.cursor()
        cur.execute('DELETE FROM publish_records WHERE id = ?', (rid,))
        conn.commit()
        conn.close()
        return jsonify({'code': 200, 'msg': 'ok'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)}), 500

@app.route('/savePublishRecord', methods=['POST'])
def save_publish_record():
    """新建发布记录（发布前调用）"""
    data = request.get_json()
    try:
        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO publish_records (title, file_path, platform, account_name, status)
            VALUES (?, ?, ?, ?, 0)
        """, (data.get('title'), data.get('file_path'), data.get('platform'), data.get('account_name')))
        record_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "data": {"id": record_id}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/updatePublishRecord', methods=['POST'])
def update_publish_record():
    """更新发布记录状态"""
    data = request.get_json()
    try:
        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        cur = conn.cursor()
        cur.execute("""
            UPDATE publish_records SET status=?, error_msg=? WHERE id=?
        """, (data.get('status'), data.get('error_msg', ''), data.get('id')))
        conn.commit()
        conn.close()
        return jsonify({"code": 200})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/saveDraft', methods=['POST'])
def save_draft():
    """保存草稿"""
    data = request.get_json()
    try:
        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO drafts (tab_key, title, content, platform, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tab_key) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                platform=excluded.platform,
                updated_at=CURRENT_TIMESTAMP
        """, (data.get('tab_key'), data.get('title'), data.get('content'), data.get('platform')))
        conn.commit()
        conn.close()
        return jsonify({"code": 200})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/getDrafts', methods=['GET'])
def get_drafts():
    """获取所有草稿"""
    try:
        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM drafts ORDER BY updated_at DESC")
        rows = cur.fetchall()
        conn.close()
        drafts = [dict(row) for row in rows]
        return jsonify({"code": 200, "data": drafts})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/deleteDraft', methods=['POST'])
def delete_draft():
    """删除草稿"""
    data = request.get_json()
    try:
        conn = sqlite3.connect(str(BASE_DIR / 'database.db'))
        cur = conn.cursor()
        cur.execute("DELETE FROM drafts WHERE tab_key=?", (data.get('tab_key'),))
        conn.commit()
        conn.close()
        return jsonify({"code": 200})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ========== end AI 创作者中心 ==========

if __name__ == '__main__':
    app.run(host='0.0.0.0' ,port=5409)
