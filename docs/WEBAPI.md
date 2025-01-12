# Web API Planning Document

## 1. Summary of Goals & Approach

We want to evolve our existing command-line YouTube Playlist Organizer into a web-accessible backend service. The main goals are:
- Provide a programmatic interface (REST API) that encapsulates the same functionality currently exposed by the CLI.  
- Allow web clients (and, in the future, a SwiftUI client) to call into the same code.  
- Maintain all existing functionality and documentation.  
- Keep our code clean, modular, and well-tested.

<details>
<summary><strong>[Educational Context]</strong></summary>
This means you don’t have to rewrite large parts of the application. Instead, you’ll introduce a minimal web framework (e.g., Flask, FastAPI) that wraps existing functionality. This separation of concerns allows the CLI to remain fully operational while enabling new opportunities to integrate with frontends.
</details>

## 2. Planned Enhancements

Below are the proposed enhancements to introduce a Web API layer:

1. **New “webapi.py” File (or similar) in the “src” Folder**  
   - Set up a Python web framework. Let's use FastAPI.
   - Define HTTP endpoints that correspond to existing commands (e.g., “/consolidate”, “/deduplicate”, “/distribute”).  
   - Parse JSON request bodies, build appropriate command objects with the parameters, and execute them.  
   - Return JSON responses containing the result (list of videos processed, errors, etc.).

2. **Preserve Existing CLI**  
   - No changes needed in the CLI code.  
   - The new web API endpoints will call the exact same consolidate/distribute/deduplicate logic that the CLI commands use.

3. **Update Documentation**  
   - Reference this new file (WEBAPI.md) from the README and docs/INSTALLATION.md.  
   - Show how to install the new dependencies and run the application in “web mode.”  

4. **Testing & Validation**  
   - Write basic integration tests (with pytest) that spin up the web server in test mode, issue mock HTTP requests, and validate responses.  
   - All existing tests must still pass to ensure no breakage.  

<details>
<summary><strong>[Educational Context]</strong></summary>
“Enhancements” are not entirely new features but augmentations to existing code. Think of them as adding a new “front door” to the same building rather than renovating the entire structure. We continue to rely on the existing command pattern and do not remove or alter it.
</details>

## 3. Implementation Steps (For a Junior Developer)

These instructions outline how to implement the Web API endpoint by reusing existing code:

### Step 1: Create “webapi.py” (or “server.py”) 
1. Choose a framework (Flask or FastAPI). Suppose we use FastAPI for illustration.  
2. Install necessary packages:  
   ```bash
   uv pip install fastapi uvicorn
   ```  
   (Using “uv” as per our project’s Python dependency guidelines.)

3. Create a new file: “src/youtubesorter/webapi.py”  
4. Define a FastAPI application, import code from “consolidate.py,” “distribute.py,” etc.  
5. For each major function (consolidate, distribute, deduplicate), add a REST endpoint that receives JSON request data and calls the existing code.  
6. Return structured JSON responses that detail whether the operation succeeded.  

<details>
<summary><strong>[Educational Context]</strong></summary>
A “web framework” like FastAPI listens on a URL host/port for incoming requests. It converts incoming JSON data to Python objects, calls your Python functions, and then serializes the results back to JSON. This is how we expose a REST API without rewriting the entire codebase.
</details>

### Step 2: Link Commands to Endpoints
1. Within “webapi.py,” write route handlers analogous to CLI commands. Example (pseudocode):  
   ```python
   from fastapi import FastAPI
   from pydantic import BaseModel
   from . import consolidate

   app = FastAPI()

   class ConsolidateRequest(BaseModel):
       source_playlists: list[str]
       target_playlist: str
       filter_prompt: str

   @app.post("/consolidate")
   def consolidate_endpoints(req: ConsolidateRequest):
       # Possibly validate arguments here
       results = consolidate.consolidate_playlists(
           source_playlists=req.source_playlists,
           target_playlist=req.target_playlist,
           prompt=req.filter_prompt,
       )
       return {"status": "success", "details": results}
   ```
2. Repeat this pattern for “distribute”, “deduplicate”, etc.  
3. Make sure to handle errors gracefully and return JSON with helpful error messages.

### Step 3: Spin Up the Server
1. In “pyproject.toml” or “requirements.txt,” ensure you’ve added “fastapi” and “uvicorn”.  
2. Document in “README.md” how to run:  
   ```bash
   uv python -m uvicorn youtubesorter.webapi:app --host 0.0.0.0 --port 8080
   ```

<details>
<summary><strong>[Educational Context]</strong></summary>
This runs the web server on port 8080. If you access “http://localhost:8080/consolidate” with a POST request (e.g., from Postman or cURL), it will parse your JSON body, call the “consolidate” logic, and respond with JSON.
</details>

### Step 4: Testing
1. **Existing Unit Tests**:  
   • Run the normal test suite to verify nothing is broken.  

2. **New Web Tests**:  
   • Create a dedicated test file “test_webapi.py”.  
   • Use “TestClient” from FastAPI or “requests” library to make requests to your local server.  
   • For example:  
     ```python
     from fastapi.testclient import TestClient
     from src.youtubesorter.webapi import app

     client = TestClient(app)

     def test_consolidate_endpoint():
         response = client.post("/consolidate", json={
             "source_playlists": ["PL1", "PL2"],
             "target_playlist": "PL_TARGET",
             "filter_prompt": "coding tutorials"
         })
         assert response.status_code == 200
         data = response.json()
         assert data["status"] == "success"
     ```
3. **Integration Tests**:  
   • If you’re using real YouTube credentials, confirm the correct operations happen.  
   • Optionally mock the YouTube calls if you want to avoid quota usage in integration tests.  

<details>
<summary><strong>[Educational Context]</strong></summary>
By introducing automated tests for the new endpoints, you ensure reliability and avoid regressions. The same concept used to test CLI commands—verifying input and output—applies to HTTP endpoints, only the input and output are JSON rather than command-line arguments.
</details>

## 4. Future Considerations

1. **Authentication & Authorization**  
   - Once a broader audience uses this API, consider adding token-based auth or OAuth flows.  
2. **Scaling & Deployment**  
   - If you anticipate significant traffic, think about containerizing (Docker) or using a cloud platform.  
3. **SwiftUI Integration**  
   - The SwiftUI client can call the same REST endpoints. Implementation details will depend on Swift’s “URLSession,” decoding JSON, etc.  

<details>
<summary><strong>[Educational Context]</strong></summary>
Once your backend is an HTTP API, you can connect any modern front-end to it. SwiftUI, React, Vue, or plain JavaScript all speak HTTP.
</details>

---

## Final Notes
- **No Drastic Refactors:** This strategy avoids rewriting existing code and reduces the risk of breaking current features.  
- **Maintain Docs and Tests:** Keep “docs/INSTALLATION.md” and “README.md” updated. Add usage examples for the new server mode. Ensure the test suite covers this new functionality.  
- **Ask Questions**: If something is unclear, ask for help. That’s better than guessing and introducing regressions. 