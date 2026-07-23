import aiohttp
from config import SMM_API_URL, SMM_API_KEY


class SMMApiError(Exception):
    pass


async def _post(data: dict):
    payload = {"key": SMM_API_KEY, **data}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SMM_API_URL, data=payload, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                try:
                    result = await resp.json(content_type=None)
                except Exception:
                    text = await resp.text()
                    raise SMMApiError(f"Noto'g'ri javob: {text[:200]}")
    except aiohttp.ClientError as e:
        raise SMMApiError(f"API bilan bog'lanishda xatolik: {e}")

    if isinstance(result, dict) and result.get("error"):
        raise SMMApiError(str(result["error"]))
    return result


async def get_services():
    return await _post({"action": "services"})


async def add_order(service: int, link: str, quantity: int):
    return await _post({"action": "add", "service": service, "link": link, "quantity": quantity})


async def add_package_order(service: int, link: str):
    return await _post({"action": "add", "service": service, "link": link})


async def add_comments_order(service: int, link: str, comments: str):
    return await _post({"action": "add", "service": service, "link": link, "comments": comments})


async def add_poll_order(service: int, link: str, quantity: int, answer_number: int):
    return await _post(
        {
            "action": "add",
            "service": service,
            "link": link,
            "quantity": quantity,
            "answer_number": answer_number,
        }
    )


async def order_status(order_id: int):
    return await _post({"action": "status", "order": order_id})


async def get_balance():
    return await _post({"action": "balance"})
