import asyncio, json
from dataclasses import is_dataclass, asdict
from typing import Any, Awaitable, Iterable, List, Optional
from tqdm import tqdm

def _to_jsonable(x: Any) -> Any:
    if hasattr(x, "model_dump") and callable(x.model_dump):  # pydantic v2
        return x.model_dump()
    if hasattr(x, "dict") and callable(x.dict):              # pydantic v1
        return x.dict()
    if is_dataclass(x):
        return asdict(x)
    return x

def save_json_array(items: Iterable[Any], path: str, indent: int = 4) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([_to_jsonable(it) for it in items], f, indent=indent, ensure_ascii=False)

async def run_concurrent_tasks(
    tasks: Iterable[Awaitable[Any]],
    max_concurrent: int,
    description: Optional[str] = None,
    return_exceptions: bool = True,
) -> List[Any]:
    sem = asyncio.Semaphore(max_concurrent)
    tasks = list(tasks)
    pbar = tqdm(total=len(tasks), desc=description or "Working")

    async def _limited(coro):
        async with sem:
            return await coro

    async def _runner(coro):
        try:
            return await _limited(coro)
        finally:
            pbar.update(1)

    try:
        return await asyncio.gather(*[_runner(c) for c in tasks], return_exceptions=return_exceptions)
    finally:
        pbar.close()
