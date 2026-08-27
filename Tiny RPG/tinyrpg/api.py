from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def welcome_to_tiny_rpg() -> dict[str, str]:
    return {"message": "Welcome to TinyRPG"}
