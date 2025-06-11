import hashlib
import hmac
import os
from typing import Annotated, Literal

import boto3
from anima.smiles import SMILES
from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, Field


def get_secret_from_ssm(param_name: str, region: str = "eu-north-1") -> str:
    """
    Retrieve a SecureString parameter from AWS SSM Parameter Store.

    The parameter value is automatically decrypted using the KMS key specified
    during creation.
    """
    ssm_client = boto3.client("ssm", region_name=region)
    response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]


SSM_PARAM_NAME = os.environ.get("SECRET_KEY_PARAM_NAME", "")
SECRET_KEY = get_secret_from_ssm(SSM_PARAM_NAME)

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


def safe_check(client_key: str, stored_key: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(client_key.encode()).digest(),
        hashlib.sha256(stored_key.encode()).digest(),
    )


def verify_key(request: Request) -> Literal[True]:
    client_key = request.headers.get("SMILES_API_KEY")
    if not client_key or not safe_check(client_key, SECRET_KEY):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True


@app.post("/transform-smiles", status_code=status.HTTP_200_OK)
def prepare_and_transform(
    valid: Annotated[bool, Depends(verify_key)],
    payload: Annotated[Payload, Body(...)],
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
async def index(valid: Annotated[bool, Depends(verify_key)], /) -> dict[str, str]:
    return {
        "info": "SMILES-API up",
    }


# the aws handler
def lambda_handler(event, context):
    handler = Mangum(app)
    return handler(event, context)
