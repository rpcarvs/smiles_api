import hashlib
import hmac
from typing import Annotated

import azure.functions as func
import uvicorn
from anima.smiles import SMILES
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

VAULT_URL = "https://rodc-kv.vault.azure.net/"
SECRET_NAME = "smilestoken"


credential = DefaultAzureCredential()
client = SecretClient(vault_url=VAULT_URL, credential=credential)
SECRET_KEY = client.get_secret(SECRET_NAME).value

sml = SMILES()
app = FastAPI(title="SMILES-API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

max_length = 54
vocab = [
    "#",
    "(",
    ")",
    "1",
    "2",
    "3",
    "=",
    "Br",
    "C",
    "Cl",
    "F",
    "N",
    "O",
    "S",
    "[nH]",
    "c",
    "n",
    "o",
    "s",
]


# Model for data validation
class Payload(BaseModel):
    smiles: Annotated[str, Field(max_length=max_length)]


def safe_check(client_key, stored_key):
    return hmac.compare_digest(
        hashlib.sha256(client_key.encode()).digest(),
        hashlib.sha256(stored_key.encode()).digest(),
    )


def verify_key(request: Request):
    client_key = request.headers.get("SMILES_API_KEY")
    if not client_key or not safe_check(client_key, SECRET_KEY):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True


@app.post("/transform-smiles", status_code=status.HTTP_200_OK)
def prepare_and_transform(
    __valid: bool = Depends(verify_key),
    payload: Payload = Body(...),
):
    try:
        molecule = payload.smiles
        try:
            message = sml.transform(molecule, vocab)
        except Exception:
            message = sml.transform(molecule, vocab, fix=True)
    except Exception:
        return HTTPException(status_code=401, detail="Not a valid SMILES!")

    return {"smiles": message}


@app.get("/", status_code=status.HTTP_200_OK)
async def index(__valid: bool = Depends(verify_key)):
    return {
        "info": "SMILES-API up",
    }


# Wrap FastAPI app with Azure Functions
function_app = func.AsgiFunctionApp(app=app, http_auth_level=func.AuthLevel.ANONYMOUS)


if __name__ == "__main__":
    uvicorn.run("smiles_api:app", host="0.0.0.0", port=80)
