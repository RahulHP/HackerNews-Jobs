def lambda_handler(event, context):
    # Confirm the user
    event['response']['autoConfirmUser'] = True
    return event
