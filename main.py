import os
import asyncio
import aiofiles
import json

from telethon import TelegramClient
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from core.SendFile import Send, Split
from core.GetFile import Get, Merge
from database.Database import (create_db_and_tables, add_user_to_db, add_file_to_db, 
                               get_user_files, get_file_by_id, delete_file, get_user_by_name, 
                               verify_password, get_uuid_by_name
)
load_dotenv()

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
session_name = 'test'

upload_progress: dict = {}

client = TelegramClient(session_name, api_id, api_hash)

# call functions on startup
@asynccontextmanager
async def start(app: FastAPI):
    await create_db_and_tables() # Add a database (if none)
    await client.start() # await client.start()
    yield
    await client.disconnect() # if server off

app = FastAPI(lifespan=start)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.cookies.get("session_username"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    existing_user = await get_user_by_name(username)
    if existing_user:
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "This username is already taken"}
        )

    try:
        await add_user_to_db(username, password)
    except Exception as e:
        print(f"Error: {e}")
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Error creating account"}
        )
    # Autologin (If the user is in the cookie files)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session_username", value=username, httponly=True, max_age=86400)
    return response

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await get_user_by_name(username)
    
    if user and verify_password(password, user.password_hash):
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session_username", value=username, httponly=True, max_age=86400)
        return response
    else:
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Incorrect username or password"}
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    username = request.cookies.get("session_username")
    if not username:
        return RedirectResponse(url="/", status_code=303)
    
    files = await get_user_files(username)
    
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={"username": username, "files": files}
    )

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    # delete cookies
    response.delete_cookie("session_username")
    return response

@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    username = request.cookies.get("session_username")
    if not username:
        raise HTTPException(status_code=401)
    
    uuid = await get_uuid_by_name(username)
    upload_progress[username] = {"pct": 0, "done": False, "error": False}
    
    temp_path = f"/tmp/{uuid}_{file.filename}"

    try:
        # Bug #3 fix: stream to disk in 1MB pieces, don't load entire file into memory
        async with aiofiles.open(temp_path, "wb") as buffer:
            while chunk_data := await file.read(1024 * 1024):
                await buffer.write(chunk_data)

        file_size = os.path.getsize(temp_path)
        MB = 1024**2
        if file_size <= 10 * MB:
            chunks_size = 1 * MB
        elif file_size <= 50 * MB:
            chunks_size = 2 * MB
        elif file_size <= 100 * MB:
            chunks_size = 5 * MB
        elif file_size <= 1000 * MB:
            chunks_size = 10 * MB
        else:
            chunks_size = 20 * MB

        chunks = await Split(temp_path, chunks_size)
        total = len(chunks)

        upload_progress[username]["pct"] = 5

        # Bug #1 fix: collect message ids returned by Send()
        sent = 0
        currentid_chunk_list = []
        for chunk in chunks:
            try:
                msg = await Send(client, "me", chunk)
                if not msg:
                    raise Exception("Send failed")
                currentid_chunk_list.append(msg.id)
                sent += 1
                upload_progress[username]["pct"] = 5 + int((sent / total) * 90)
            finally:
                # Bug #4 fix: always clean up chunk files, even on error
                if os.path.exists(chunk):
                    os.remove(chunk)

        await add_file_to_db(username, file.filename, currentid_chunk_list)
        upload_progress[username] = {"pct": 100, "done": True, "error": False}

    except Exception as e:
            import traceback
            traceback.print_exc()  # <-- вот сюда
            upload_progress[username] = {"pct": 0, "done": False, "error": True}
            raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        # Bug #4 fix: always clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {"ok": True}

@app.get("/upload/progress")
async def upload_progress_stream(request: Request):
    username = request.cookies.get("session_username")
    if not username:
        raise HTTPException(status_code=401)

    async def event_stream():
        while True:
            if await request.is_disconnected():
                break
            state = upload_progress.get(username, {"pct": 0, "done": False, "error": False})
            yield f"data: {json.dumps(state)}\n\n"
            if state.get("done") or state.get("error"):
                upload_progress.pop(username, None)
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/download")
async def download_file(file_id: int = Form(...)):
    db_file = await get_file_by_id(file_id)

    ids = db_file.id_chunk_list
    output_name = db_file.file_name
    
    chunks = []
    for msg_id in ids:
        path = await Get(client, "me", int(msg_id))
        if path:
            chunks.append(path)
    
    if chunks:
        Merge(chunks, output_name)
    
    return FileResponse(
        path=output_name, 
        filename=output_name, 
        background=BackgroundTasks().add_task(os.remove, output_name)
    )

@app.post("/delete")
async def delete_file_endpoint(file_id: int = Form(...)):
    # Get file id
    db_file = await get_file_by_id(file_id)
    # If file none in DB
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        await client.delete_messages("me", db_file.id_chunk_list) # Delete message
        await delete_file(file_id)
        return RedirectResponse(url="/", status_code=303)
        
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error deleting from the server")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)