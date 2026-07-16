from fastapi.testclient import TestClient

import main


with TestClient(main.app) as client:
    root_response = client.get("/")
    print("GET /", root_response.status_code, root_response.json())

    create_response = client.post(
        "/books",
        json={
            "title": "The Pragmatic Programmer",
            "author": "Andy Hunt",
            "published_year": 1999,
        },
    )
    print("POST /books", create_response.status_code, create_response.json())
    created_book = create_response.json()
    book_id = created_book["id"]

    list_response = client.get("/books")
    print("GET /books", list_response.status_code, list_response.json())

    get_response = client.get(f"/books/{book_id}")
    print(f"GET /books/{book_id}", get_response.status_code, get_response.json())

    update_response = client.put(
        f"/books/{book_id}",
        json={
            "title": "The Pragmatic Programmer 20th Anniversary Edition",
            "author": "Andy Hunt",
            "published_year": 2019,
        },
    )
    print(f"PUT /books/{book_id}", update_response.status_code, update_response.json())

    delete_response = client.delete(f"/books/{book_id}")
    print(f"DELETE /books/{book_id}", delete_response.status_code)
