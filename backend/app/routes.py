from flask import Blueprint, request, jsonify
from .services.openai_service import evaluate_document
from .services.health_service import check_health
from http import HTTPStatus

api = Blueprint('api', __name__)

@api.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    is_healthy = check_health()
    return jsonify({'status': 'healthy' if is_healthy else 'unhealthy'}), \
           HTTPStatus.OK if is_healthy else HTTPStatus.SERVICE_UNAVAILABLE

@api.route('/openai/evaluate', methods=['POST'])
def evaluate():
    """OpenAI APIを使用して文書を評価する"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'リクエストボディが空です'}), HTTPStatus.BAD_REQUEST

        # 必須フィールドの検証
        required_fields = ['model', 'messages', 'max_tokens', 'temperature']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': f'必須フィールドが不足しています: {", ".join(missing_fields)}'
            }), HTTPStatus.BAD_REQUEST

        # OpenAI APIを使用して評価を実行
        result = evaluate_document(data)
        return jsonify(result), HTTPStatus.OK

    except Exception as e:
        return jsonify({'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR 