"""
ベクトルストア

ChromaDBを使用して会議履歴をベクトル化し、類似検索を実現します。
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MeetingVectorStore:
    """会議履歴のベクトルストア"""
    
    def __init__(self, persist_directory: str = "data/chroma"):
        """
        初期化
        
        Args:
            persist_directory: ChromaDBの永続化ディレクトリ
        """
        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # ChromaDBとEmbeddingモデルを遅延初期化
        self._client = None
        self._collection = None
        self._embeddings = None
        
        logger.info(f"MeetingVectorStore initialized: {persist_directory}")
    
    def _initialize(self):
        """ChromaDBとEmbeddingモデルを初期化"""
        if self._client is not None:
            return
        
        try:
            import chromadb
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            # ChromaDBクライアントを初期化
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            
            # コレクションを取得または作成
            self._collection = self._client.get_or_create_collection(
                name="meetings",
                metadata={"description": "Meeting transcripts and summaries"}
            )
            
            # Embeddingモデルを初期化（多言語対応）
            self._embeddings = HuggingFaceEmbeddings(
                model_name="intfloat/multilingual-e5-small",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            logger.info("ChromaDB and Embedding model initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_meeting(
        self,
        meeting_id: str,
        bot_id: str,
        meeting_title: str,
        summary: str,
        transcripts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        会議をベクトルストアに追加
        
        Args:
            meeting_id: 会議ID
            bot_id: ボットID
            meeting_title: 会議タイトル
            summary: 会議の要約
            transcripts: 文字起こしのリスト
            metadata: 追加のメタデータ
        """
        self._initialize()
        
        try:
            # 要約をベクトル化して追加
            summary_embedding = self._embeddings.embed_query(summary)
            
            # メタデータを準備
            doc_metadata = {
                "meeting_id": meeting_id,
                "bot_id": bot_id,
                "meeting_title": meeting_title,
                "type": "summary"
            }
            if metadata:
                doc_metadata.update(metadata)
            
            # ChromaDBに追加
            self._collection.add(
                ids=[f"meeting_{meeting_id}_summary"],
                embeddings=[summary_embedding],
                documents=[summary],
                metadatas=[doc_metadata]
            )
            
            logger.info(f"Added meeting {meeting_id} to vector store")
            
            # 文字起こしも追加（オプション）
            if transcripts:
                # 文字起こしを結合
                full_transcript = "\n".join(transcripts)
                transcript_embedding = self._embeddings.embed_query(full_transcript)
                
                transcript_metadata = {
                    "meeting_id": meeting_id,
                    "bot_id": bot_id,
                    "meeting_title": meeting_title,
                    "type": "transcript"
                }
                
                self._collection.add(
                    ids=[f"meeting_{meeting_id}_transcript"],
                    embeddings=[transcript_embedding],
                    documents=[full_transcript],
                    metadatas=[transcript_metadata]
                )
                
                logger.info(f"Added transcript for meeting {meeting_id}")
            
        except Exception as e:
            logger.error(f"Failed to add meeting to vector store: {e}")
            raise
    
    def search_similar_meetings(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        類似会議を検索
        
        Args:
            query: 検索クエリ
            n_results: 取得件数
            filter_metadata: メタデータフィルター
            
        Returns:
            List[Dict[str, Any]]: 類似会議のリスト
        """
        self._initialize()
        
        try:
            # クエリをベクトル化
            query_embedding = self._embeddings.embed_query(query)
            
            # 検索
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            
            # 結果を整形
            similar_meetings = []
            for i in range(len(results['ids'][0])):
                similar_meetings.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            
            logger.info(f"Found {len(similar_meetings)} similar meetings for query: {query[:50]}...")
            return similar_meetings
            
        except Exception as e:
            logger.error(f"Failed to search similar meetings: {e}")
            return []
    
    def get_meeting_context(
        self,
        current_transcripts: List[str],
        n_results: int = 3
    ) -> str:
        """
        現在の会議に関連する過去の会議コンテキストを取得
        
        Args:
            current_transcripts: 現在の会議の文字起こし
            n_results: 取得件数
            
        Returns:
            str: 過去の会議コンテキスト
        """
        self._initialize()
        
        # 現在の会議内容を要約
        query = "\n".join(current_transcripts[-10:])  # 最新10件
        
        # 類似会議を検索
        similar_meetings = self.search_similar_meetings(
            query=query,
            n_results=n_results,
            filter_metadata={"type": "summary"}
        )
        
        if not similar_meetings:
            return ""
        
        # コンテキストを構築
        context_parts = ["過去の類似会議:"]
        for i, meeting in enumerate(similar_meetings, 1):
            metadata = meeting['metadata']
            document = meeting['document']
            context_parts.append(
                f"\n{i}. {metadata.get('meeting_title', 'Untitled')}\n"
                f"   要約: {document[:200]}..."
            )
        
        return "\n".join(context_parts)
    
    def delete_meeting(self, meeting_id: str):
        """
        会議をベクトルストアから削除
        
        Args:
            meeting_id: 会議ID
        """
        self._initialize()
        
        try:
            # 要約と文字起こしを削除
            self._collection.delete(
                ids=[
                    f"meeting_{meeting_id}_summary",
                    f"meeting_{meeting_id}_transcript"
                ]
            )
            logger.info(f"Deleted meeting {meeting_id} from vector store")
            
        except Exception as e:
            logger.error(f"Failed to delete meeting from vector store: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        self._initialize()
        
        try:
            count = self._collection.count()
            return {
                "total_documents": count,
                "collection_name": self._collection.name
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
