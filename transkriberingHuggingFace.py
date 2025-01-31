import requests
import os, dotenv

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_NBTRANSKRIPT_URL = os.getenv("HF_NBTRANSKRIPT_URL")

API_URL = HF_NBTRANSKRIPT_URL
headers = {
	"Accept" : "application/json",
	"Authorization": "Bearer " + HUGGINGFACE_API_KEY,
	"Content-Type": "audio/mpeg" 
}

def query(filename):
	with open(filename, "rb") as f:
		data = f.read()
	response = requests.post(API_URL, headers=headers, data=data)
	return response.json()

output = query("./lyd/<lydfil>.mp3")
print(output)