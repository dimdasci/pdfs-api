import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO) # Adjust level based on env var later if needed

# --- Stub Functions (extracted from previous handlers) ---

def handle_upload(event):
    logger.info("Handling POST /documents")
    document_id = "stub-doc-123"
    status = "UPLOADED"
    response_body = {"document_id": document_id, "status": status}
    return 201, response_body

def handle_list(event):
    logger.info("Handling GET /documents")
    # status_filter = event.get('queryStringParameters', {}).get('status')
    stub_documents = [
        {"document_id": "stub-doc-123", "name": "example.pdf", "status": "PROCESSING"},
        {"document_id": "stub-doc-456", "name": "another.pdf", "status": "COMPLETE"}
    ]
    return 200, stub_documents

def handle_get_manifest(event):
    doc_id = event.get('pathParameters', {}).get('docId')
    logger.info(f"Handling GET /documents/{doc_id}")
    if not doc_id:
        return 400, {"error": "Missing docId path parameter"}
    
    if doc_id == "stub-doc-123":
        response_body = {
            "document_id": doc_id,
            "name": "example.pdf",
            "page_count": 5,
            "page_sizes": [{"width": 612, "height": 792}],
            "status": "PROCESSING"
        }
        return 200, response_body
    else:
        return 404, {"error": f"Document {doc_id} not found"}

def handle_get_page_bundle(event):
    path_params = event.get('pathParameters', {})
    doc_id = path_params.get('docId')
    page_str = path_params.get('page')
    logger.info(f"Handling GET /documents/{doc_id}/pages/{page_str}")

    if not doc_id or not page_str:
        return 400, {"error": "Missing docId or page path parameter"}

    try:
        page = int(page_str)
    except ValueError:
        return 400, {"error": "Invalid page number format"}

    if doc_id == "stub-doc-123" and 1 <= page <= 5:
        response_body = {
            "document_id": doc_id,
            "page": page,
            "size": { "width": 612, "height": 792 },
            "full_raster_url": f"https://s3.placeholder.url/raster/{doc_id}/page{page}/full.png?sig=placeholder",
            "layers": [
                { "z_index": 1, "type": "path", "url": f"https://s3.placeholder.url/layer/{doc_id}/page{page}/layer-z01.png?sig=placeholder", "object_count": 10 + page },
                { "z_index": 2, "type": "text", "url": f"https://s3.placeholder.url/layer/{doc_id}/page{page}/layer-z02.png?sig=placeholder", "object_count": 50 + page }
            ],
            "objects": [
                { "id": f"obj_stub_{page}_1", "type": "text", "bbox": [100.0 + page, 700.0, 120.0 + page, 710.0], "z_index": 2 },
                { "id": f"obj_stub_{page}_2", "type": "path", "bbox": [50.0, 50.0 + page, 150.0, 150.0 + page], "z_index": 1 }
            ]
        }
        return 200, response_body
    elif doc_id != "stub-doc-123":
        return 404, {"error": f"Document {doc_id} not found"}
    else:
         return 404, {"error": f"Page {page} not found for document {doc_id}"}

# --- Router --- 

def lambda_handler(event, context):
    """Handles all incoming API Gateway requests and routes them."""
    logger.info("Received event: %s", json.dumps(event))

    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    path = event.get('requestContext', {}).get('http', {}).get('path')
    
    status_code = 500
    response_body = {"error": "Internal server error"}

    try:
        # Simple path-based routing
        if path == '/documents':
            if http_method == 'POST':
                status_code, response_body = handle_upload(event)
            elif http_method == 'GET':
                status_code, response_body = handle_list(event)
            else:
                status_code = 405 # Method Not Allowed
                response_body = {"error": f"Method {http_method} not allowed for {path}"}
        
        # Using pathParameters check for specific document/page routes
        elif 'docId' in event.get('pathParameters', {}):
            if 'page' in event.get('pathParameters', {}):
                 if http_method == 'GET':
                     status_code, response_body = handle_get_page_bundle(event)
                 else:
                     status_code = 405
                     response_body = {"error": f"Method {http_method} not allowed for {path}"}
            else: # Only docId is present
                 if http_method == 'GET':
                     status_code, response_body = handle_get_manifest(event)
                 else:
                     status_code = 405
                     response_body = {"error": f"Method {http_method} not allowed for {path}"}
        else:
            status_code = 404
            response_body = {"error": f"Path {path} not found"}

    except Exception as e:
        logger.exception("Error handling request")
        # Keep status_code 500 and default error message
        pass # Error already logged, return 500

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*" # Replace with !Ref CorsAllowedOrigin later via env var
        },
        "body": json.dumps(response_body)
    } 