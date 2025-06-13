1. [X] For documents in the dynamodb use snake_case for the keys, like user_id instead of UserId, and lower cased. Uploaded must be renamed to created_at
2. [X] Add document size in to the Document model and dynamodb table
3. [X] Save document fields to S3 object as custom metadata
4. [X] Create document id as a hash of url or binary data to avoid collisions in a user scope. 