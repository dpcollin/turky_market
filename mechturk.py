import boto.mturk.connection
import boto.mturk.question
import boto.mturk.layoutparam
import xml.etree.ElementTree as ET

from boto.mturk import layoutparam
from boto.mturk.price import Price

sandbox_host = 'mechanicalturk.sandbox.amazonaws.com'
real_host = 'mechanicalturk.amazonaws.com'

layout_id = '3YIM00EFYWY65UI7K4W5B889X9LW0Q'

mturk = boto.mturk.connection.MTurkConnection(
    aws_access_key_id='',
    aws_secret_access_key='',
    host=sandbox_host,
    debug=1)


def createhit(url,case_id):
    title = "Determine who is more likely to be telling the truth about a transaction"
    description = "(Only once, all subsequent submissions rejected) Read through the submitted summaries and look at the other document to determine which party in the transaction you feel is being truthful based on the information provided in the attached url"
    keywords = ["survey","analysis"]
    frame_height = 500 # the height of the iframe holding the external hit
    amount = .05

    params = [
      layoutparam.LayoutParameter(
        'case_id',
        case_id),
      layoutparam.LayoutParameter(
        'link',
        url)
    ]

    create_hit_result = mturk.create_hit(
        hit_layout=layout_id,
        layout_params=layoutparam.LayoutParameters(params),
        title=title,
        description=description,
        keywords=keywords,
        max_assignments=5,
        question=questionform,
        reward=Price(amount=amount),
        lifetime=datetime.timedelta(days=1),
        duration=datetime.timedelta(minutes=5),
        approval_delay=datetime.timedelta(days=2),

    )

    return create_hit_result

def processhit(hit_result):
    id = hit_result['HIT']['HITId']
    assign = mturk.get_assignments(id)
    buyer = 0
    seller = 0
    for value in assign:
        user_response = value.fields[0]
        if user_response == 'Buyer':
            buyer = buyer + 1
        else:
            seller = seller + 1
    return seller >= buyer #buyer be a little bit ware?