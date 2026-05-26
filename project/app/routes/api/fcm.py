from flask import request, jsonify
from flask_jwt_extended import jwt_required
from ...models import db
from . import api_bp, get_current_user
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/fcm/register', methods=['POST'])
@jwt_required()
def register_fcm():
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    token = data.get('token', '').strip()
    platform = data.get('platform', 'android')

    if not token:
        return jsonify(success=False, message='Token diperlukan'), 400

    try:
        from ...models import FCMToken
        existing = FCMToken.query.filter_by(token=token).first()
        if existing:
            existing.user_id = user.id
            existing.platform = platform
            existing.aktif = True
        else:
            fcm = FCMToken(token=token, user_id=user.id, platform=platform)
            db.session.add(fcm)
        db.session.commit()

        return jsonify(success=True, message='FCM token registered')
    except Exception as e:
        db.session.rollback()
        logger.exception('FCM register failed')
        return jsonify(success=False, message=str(e)), 500


@api_bp.route('/fcm/unregister', methods=['POST'])
@jwt_required()
def unregister_fcm():
    data = request.get_json()
    if not data:
        return jsonify(success=False, message='Request body required'), 400

    token = data.get('token', '').strip()
    if not token:
        return jsonify(success=False, message='Token diperlukan'), 400

    try:
        from ...models import FCMToken
        fcm = FCMToken.query.filter_by(token=token).first()
        if fcm:
            fcm.aktif = False
            db.session.commit()
        return jsonify(success=True, message='FCM token unregistered')
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e)), 500


@api_bp.route('/fcm/send-test', methods=['POST'])
@jwt_required()
def send_test_fcm():
    user = get_current_user()
    if not user.is_admin():
        return jsonify(success=False, message='Forbidden'), 403

    data = request.get_json() or {}
    title = data.get('title', 'Test Notification')
    body = data.get('body', 'This is a test push notification')

    try:
        from ...models import FCMToken
        tokens = FCMToken.query.filter_by(aktif=True).all()
        if not tokens:
            return jsonify(success=False, message='No registered FCM tokens'), 404

        import firebase_admin
        from firebase_admin import messaging

        if not firebase_admin._apps:
            return jsonify(success=False, message='Firebase not configured. Set GOOGLE_APPLICATION_CREDENTIALS'), 400

        sent_count = 0
        for t in tokens:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=t.token,
            )
            try:
                messaging.send(message)
                sent_count += 1
            except Exception:
                logger.warning('FCM send failed for token %s', t.token[:20])

        return jsonify(success=True, message=f'Sent to {sent_count} devices')
    except Exception as e:
        logger.exception('FCM send test failed')
        return jsonify(success=False, message=str(e)), 500
