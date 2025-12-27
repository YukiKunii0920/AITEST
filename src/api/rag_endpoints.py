"""
RAG検索エンドポイント

過去の会議履歴を検索するAPIエンドポイント
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rag.vector_store import MeetingVectorStore

logger = logging.getLogger(__name__)

# APIルーター
router = APIRouter(prefix="/rag", tags=["RAG"])

# ベクトルストアのインスタンス
vector_store = MeetingVectorStore()


class SearchRequest(BaseModel):
    """検索リクエスト"""
    query: str = Field(..., description="検索クエリ")
    n_results: int = Field(5, description="返す結果の数", ge=1, le=20)
    meeting_id: Optional[str] = Field(None, description="除外する会議ID（現在の会議）")


class SearchResult(BaseModel):
    """検索結果"""
    meeting_id: str = Field(..., description="会議ID")
    meeting_title: str = Field(..., description="会議タイトル")
    content: str = Field(..., description="関連する内容")
    similarity: float = Field(..., description="類似度スコア")
    timestamp: str = Field(..., description="タイムスタンプ")


class SearchResponse(BaseModel):
    """検索レスポンス"""
    query: str = Field(..., description="検索クエリ")
    results: List[SearchResult] = Field(..., description="検索結果")
    total: int = Field(..., description="結果の総数")


@router.post("/search", response_model=SearchResponse)
async def search_similar_meetings(request: SearchRequest):
    """
    類似会議を検索
    
    過去の会議履歴から、クエリに類似した内容を検索します。
    """
    try:
        logger.info(f"Searching for: {request.query}")
        
        # ベクトルストアから検索
        results = vector_store.search(
            query=request.query,
            n_results=request.n_results
        )
        
        # 現在の会議を除外
        if request.meeting_id:
            results = [r for r in results if r.get("meeting_id") != request.meeting_id]
        
        # レスポンスを構築
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                meeting_id=result.get("meeting_id", ""),
                meeting_title=result.get("meeting_title", ""),
                content=result.get("content", ""),
                similarity=result.get("similarity", 0.0),
                timestamp=result.get("timestamp", "")
            ))
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results)
        )
    
    except Exception as e:
        logger.error(f"Error searching meetings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_rag_statistics():
    """
    RAG統計情報を取得
    
    ベクトルストアの統計情報を返します。
    """
    try:
        stats = vector_store.get_statistics()
        return {
            "total_meetings": stats.get("total_meetings", 0),
            "total_chunks": stats.get("total_chunks", 0),
            "vector_store_initialized": vector_store.collection is not None
        }
    except Exception as e:
        logger.error(f"Error getting RAG statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class AddMeetingRequest(BaseModel):
    """会議追加リクエスト"""
    meeting_id: str = Field(..., description="会議ID")
    meeting_title: str = Field(..., description="会議タイトル")
    content: str = Field(..., description="会議内容")
    timestamp: Optional[str] = Field(None, description="タイムスタンプ")


@router.post("/add_meeting")
async def add_meeting_to_rag(request: AddMeetingRequest):
    """
    会議をRAGに追加
    
    新しい会議内容をベクトルストアに追加します。
    """
    try:
        from datetime import datetime
        
        vector_store.add_meeting(
            meeting_id=request.meeting_id,
            meeting_title=request.meeting_title,
            content=request.content,
            timestamp=request.timestamp or datetime.now().isoformat()
        )
        
        return {
            "success": True,
            "message": f"Meeting {request.meeting_id} added to RAG"
        }
    
    except Exception as e:
        logger.error(f"Error adding meeting to RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_rag_store():
    """
    RAGストアをクリア
    
    全てのベクトルデータを削除します。（開発用）
    """
    try:
        # 新しいベクトルストアを作成して置き換える
        global vector_store
        vector_store = MeetingVectorStore()
        
        return {
            "success": True,
            "message": "RAG store cleared"
        }
    
    except Exception as e:
        logger.error(f"Error clearing RAG store: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
