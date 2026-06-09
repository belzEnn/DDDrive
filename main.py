import os
import asyncio
import aiofiles
import json
from datetime import datetime, timedelta, timezone

import jwt
from telethon import TelegramClient
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from core.SendFile import Send, Split
from core.GetFile import Get, Merge
from database.Database import (create_db_and_tables, add_user_to_db, add_file_to_db,
                               get_user_files, get_file_by_id, delete_file, get_user_by_name,
                               verify_password, get_uuid_by_name, rename_file
)
load_dotenv()

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
SECRET_KEY = os.getenv('SECRET_KEY')
session_name = 'test'

upload_progress: dict = {}

client = TelegramClient(session_name, api_id, api_hash)


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(request: Request) -> str:
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_redirect(request: Request) -> str:
    """Same as get_current_user but redirects to login instead of 401 — for page routes."""
    try:
        return get_current_user(request)
    except HTTPException:
        raise HTTPException(status_code=307, headers={"Location": "/"})



def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(request: Request) -> str:
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_redirect(request: Request) -> str:
    try:
        return get_current_user(request)
    except HTTPException:
        raise HTTPException(status_code=307, headers={"Location": "/"})


@asynccontextmanager
async def start(app: FastAPI):
    await create_db_and_tables()
    await client.start()
    yield
    await client.disconnect()

app = FastAPI(lifespan=start)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    try:
        get_current_user(request)
        return RedirectResponse(url="/dashboard", status_code=303)
    except HTTPException:
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
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="token", value=create_token(username), httponly=True, max_age=86400)
    return response


@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await get_user_by_name(username)
    if user and verify_password(password, user.password_hash):
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="token", value=create_token(username), httponly=True, max_age=86400)
        return response
    else:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Incorrect username or password"}
        )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Depends(get_current_user_redirect)):
    files = await get_user_files(username)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"username": username, "files": files}
    )


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("token")
    return response


@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...), username: str = Depends(get_current_user)):
    uuid = await get_uuid_by_name(username)
    upload_progress[username] = {"pct": 0, "done": False, "error": False}

    temp_path = f"/tmp/{uuid}_{file.filename}"

    try:
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
                if os.path.exists(chunk):
                    os.remove(chunk)

        await add_file_to_db(username, file.filename, currentid_chunk_list, file_size)
        upload_progress[username] = {"pct": 100, "done": True, "error": False}

    except Exception as e:
        import traceback
        traceback.print_exc()
        upload_progress[username] = {"pct": 0, "done": False, "error": True}
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {"ok": True}


@app.get("/upload/progress")
async def upload_progress_stream(request: Request, username: str = Depends(get_current_user)):
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
async def download_file(file_id: int = Form(...), username: str = Depends(get_current_user)):
    db_file = await get_file_by_id(file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

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
async def delete_file_endpoint(file_id: int = Form(...), username: str = Depends(get_current_user)):
    db_file = await get_file_by_id(file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        await client.delete_messages("me", db_file.id_chunk_list)
        await delete_file(file_id)
        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error deleting from the server")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)