"""
وحدة إدارة العملات المشفرة والمحافظ

تدير محافظ المستخدمين ومعاملات USDT-TRC وتكامل Binance
"""

import logging
import sqlite3
import aiosqlite
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import config

# إعداد المسجل
logger = logging.getLogger("smm_bot")

async def init_crypto_tables():
    """تهيئة جداول العملات المشفرة"""
    # لا نحتاج لتشغيل migrations هنا لأنها تتم في init_all_db()
    pass

async def create_crypto_wallet(user_id: int, asset: str, network: str, 
                             address: str, tag: str = None, 
                             sub_account_id: str = None) -> int:
    """إنشاء محفظة عملة مشفرة للمستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            cursor = await db.execute(
                """INSERT INTO crypto_wallets (user_id, asset, network, address, tag, sub_account_id) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, asset, network, address, tag, sub_account_id)
            )
            await db.commit()
            wallet_id = cursor.lastrowid
            logger.info(f"تم إنشاء محفظة جديدة: {wallet_id} - {user_id} {asset}-{network}")
            return wallet_id
    except sqlite3.IntegrityError:
        logger.warning(f"محفظة موجودة بالفعل للمستخدم {user_id} {asset}-{network}")
        return -1
    except Exception as e:
        logger.error(f"خطأ في إنشاء محفظة {user_id} {asset}: {e}")
        return -1

async def get_user_wallet(user_id: int, asset: str, network: str) -> Optional[Dict[str, Any]]:
    """الحصول على محفظة المستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute(
                "SELECT * FROM crypto_wallets WHERE user_id = ? AND asset = ? AND network = ? AND is_active = 1",
                (user_id, asset, network)
            )
            wallet = await cursor.fetchone()
            
            return dict(wallet) if wallet else None
    except Exception as e:
        logger.error(f"خطأ في جلب محفظة {user_id} {asset}: {e}")
        return None

async def get_all_user_wallets(user_id: int) -> List[Dict[str, Any]]:
    """الحصول على جميع محافظ المستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute(
                "SELECT * FROM crypto_wallets WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )
            wallets = await cursor.fetchall()
            
            return [dict(wallet) for wallet in wallets]
    except Exception as e:
        logger.error(f"خطأ في جلب محافظ المستخدم {user_id}: {e}")
        return []

async def create_crypto_transaction(user_id: int, transaction_type: str, amount: float,
                                  asset: str, network: str, address: str = None,
                                  txid: str = None, status: str = 'pending',
                                  fee: float = 0, raw_data: dict = None) -> int:
    """إنشاء معاملة عملة مشفرة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            raw_data_json = json.dumps(raw_data) if raw_data else None
            
            cursor = await db.execute(
                """INSERT INTO crypto_transactions 
                   (user_id, type, amount, asset, network, address, txid, status, fee, raw_data) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, transaction_type, amount, asset, network, address, 
                 txid, status, fee, raw_data_json)
            )
            await db.commit()
            transaction_id = cursor.lastrowid
            logger.info(f"تم إنشاء معاملة جديدة: {transaction_id} - {user_id} {transaction_type} {amount} {asset}")
            return transaction_id
    except sqlite3.IntegrityError:
        logger.warning(f"معاملة مكررة بـ txid: {txid}")
        return -1
    except Exception as e:
        logger.error(f"خطأ في إنشاء معاملة {user_id}: {e}")
        return -1

async def update_crypto_transaction(transaction_id: int, status: str = None, 
                                  confirmations: int = None, txid: str = None,
                                  raw_data: dict = None, admin_id: int = None,
                                  admin_note: str = None) -> bool:
    """تحديث معاملة عملة مشفرة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            updates = []
            params = []
            
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            
            if confirmations is not None:
                updates.append("confirmations = ?")
                params.append(confirmations)
            
            if txid is not None:
                updates.append("txid = ?")
                params.append(txid)
            
            if raw_data is not None:
                updates.append("raw_data = ?")
                params.append(json.dumps(raw_data))
            
            if admin_id is not None:
                updates.append("admin_id = ?")
                params.append(admin_id)
            
            if admin_note is not None:
                updates.append("admin_note = ?")
                params.append(admin_note)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(transaction_id)
            
            query = f"UPDATE crypto_transactions SET {', '.join(updates)} WHERE id = ?"
            await db.execute(query, params)
            await db.commit()
            
            logger.info(f"تم تحديث المعاملة {transaction_id}")
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث المعاملة {transaction_id}: {e}")
        return False

async def get_crypto_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على معاملة بواسطة المعرف"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute(
                """SELECT ct.*, u.username, u.full_name 
                   FROM crypto_transactions ct 
                   LEFT JOIN users u ON ct.user_id = u.user_id 
                   WHERE ct.id = ?""",
                (transaction_id,)
            )
            transaction = await cursor.fetchone()
            
            if transaction:
                transaction_dict = dict(transaction)
                if transaction_dict.get('raw_data'):
                    try:
                        transaction_dict['raw_data'] = json.loads(transaction_dict['raw_data'])
                    except:
                        transaction_dict['raw_data'] = None
                return transaction_dict
            return None
    except Exception as e:
        logger.error(f"خطأ في جلب المعاملة {transaction_id}: {e}")
        return None

async def get_crypto_transaction_by_txid(txid: str) -> Optional[Dict[str, Any]]:
    """الحصول على معاملة بواسطة txid"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute(
                """SELECT ct.*, u.username, u.full_name 
                   FROM crypto_transactions ct 
                   LEFT JOIN users u ON ct.user_id = u.user_id 
                   WHERE ct.txid = ?""",
                (txid,)
            )
            transaction = await cursor.fetchone()
            
            if transaction:
                transaction_dict = dict(transaction)
                if transaction_dict.get('raw_data'):
                    try:
                        transaction_dict['raw_data'] = json.loads(transaction_dict['raw_data'])
                    except:
                        transaction_dict['raw_data'] = None
                return transaction_dict
            return None
    except Exception as e:
        logger.error(f"خطأ في جلب المعاملة {txid}: {e}")
        return None

async def get_user_crypto_transactions(user_id: int, transaction_type: str = None,
                                     asset: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """الحصول على معاملات المستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            query = "SELECT * FROM crypto_transactions WHERE user_id = ?"
            params = [user_id]
            
            if transaction_type:
                query += " AND type = ?"
                params.append(transaction_type)
            
            if asset:
                query += " AND asset = ?"
                params.append(asset)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            transactions = await cursor.fetchall()
            
            result = []
            for transaction in transactions:
                transaction_dict = dict(transaction)
                if transaction_dict.get('raw_data'):
                    try:
                        transaction_dict['raw_data'] = json.loads(transaction_dict['raw_data'])
                    except:
                        transaction_dict['raw_data'] = None
                result.append(transaction_dict)
            
            return result
    except Exception as e:
        logger.error(f"خطأ في جلب معاملات المستخدم {user_id}: {e}")
        return []

async def get_pending_crypto_transactions(transaction_type: str = None, 
                                        asset: str = None) -> List[Dict[str, Any]]:
    """الحصول على المعاملات المعلقة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            query = """SELECT ct.*, u.username, u.full_name 
                      FROM crypto_transactions ct 
                      LEFT JOIN users u ON ct.user_id = u.user_id 
                      WHERE ct.status = 'pending'"""
            params = []
            
            if transaction_type:
                query += " AND ct.type = ?"
                params.append(transaction_type)
            
            if asset:
                query += " AND ct.asset = ?"
                params.append(asset)
            
            query += " ORDER BY ct.created_at ASC"
            
            cursor = await db.execute(query, params)
            transactions = await cursor.fetchall()
            
            result = []
            for transaction in transactions:
                transaction_dict = dict(transaction)
                if transaction_dict.get('raw_data'):
                    try:
                        transaction_dict['raw_data'] = json.loads(transaction_dict['raw_data'])
                    except:
                        transaction_dict['raw_data'] = None
                result.append(transaction_dict)
            
            return result
    except Exception as e:
        logger.error(f"خطأ في جلب المعاملات المعلقة: {e}")
        return []

async def get_crypto_statistics() -> Dict[str, Any]:
    """الحصول على إحصائيات العملات المشفرة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            # إجمالي المحافظ النشطة
            cursor = await db.execute("SELECT COUNT(*) as count FROM crypto_wallets WHERE is_active = 1")
            total_wallets = (await cursor.fetchone())['count']
            
            # إجمالي المعاملات
            cursor = await db.execute("SELECT COUNT(*) as count FROM crypto_transactions")
            total_transactions = (await cursor.fetchone())['count']
            
            # إجمالي الإيداعات والسحوبات
            cursor = await db.execute(
                """SELECT type, SUM(amount) as total_amount, COUNT(*) as count 
                   FROM crypto_transactions 
                   WHERE status = 'completed' 
                   GROUP BY type"""
            )
            transaction_stats = {row['type']: {'amount': row['total_amount'], 'count': row['count']} 
                               for row in await cursor.fetchall()}
            
            # المعاملات المعلقة
            cursor = await db.execute(
                "SELECT COUNT(*) as count FROM crypto_transactions WHERE status = 'pending'"
            )
            pending_transactions = (await cursor.fetchone())['count']
            
            return {
                'total_wallets': total_wallets,
                'total_transactions': total_transactions,
                'transaction_stats': transaction_stats,
                'pending_transactions': pending_transactions
            }
    except Exception as e:
        logger.error(f"خطأ في جلب إحصائيات العملات المشفرة: {e}")
        return {
            'total_wallets': 0,
            'total_transactions': 0,
            'transaction_stats': {},
            'pending_transactions': 0
        }

async def deactivate_wallet(wallet_id: int) -> bool:
    """إلغاء تفعيل محفظة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute(
                "UPDATE crypto_wallets SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (wallet_id,)
            )
            await db.commit()
            logger.info(f"تم إلغاء تفعيل المحفظة {wallet_id}")
            return True
    except Exception as e:
        logger.error(f"خطأ في إلغاء تفعيل المحفظة {wallet_id}: {e}")
        return False