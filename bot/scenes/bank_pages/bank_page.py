from aiogram.types import CallbackQuery  # type: ignore
from modules.ws_client import get_company, company_pay_taxes
from oms.utils import callback_generator
from .utils.oneuser_page import OneUserPage


Page = OneUserPage

class BankPage(Page):
    __for_blocked_pages__ = ["bank-credit-page", "bank-deposit-page"]
    __page_name__ = "bank-menu"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        # Извлекаем данные
        balance = company_data.get('balance', 0)
        reputation = company_data.get('reputation', 0)
        business_type = company_data.get('business_type', 'small')
        tax_debt = company_data.get('tax_debt', 0)
        tax_rate = company_data.get('tax_rate', 0)
        credits = company_data.get('credits', [])
        deposits = company_data.get('deposits', [])
        overdue_steps = company_data.get('overdue_steps', 0)
        
        # Форматируем тип бизнеса
        business_type_text = "Малый" if business_type == "small" else "Большой"
        
        # Форматируем баланс с разделением тысяч
        balance_formatted = f"{balance:,}".replace(",", " ")
        tax_debt_formatted = f"{tax_debt:,}".replace(",", " ")
        
        # Форматируем процент налога
        tax_percent = f"{tax_rate * 100:.1f}%"
        
        # Формируем текст
        text = f"""🏦 *Банк*

*Баланс компании:* {balance_formatted} 💰
*Репутация:* {reputation} ⭐
*Тип бизнеса:* {business_type_text}
*Сумма налога:* {tax_debt_formatted} 💰
*Процент налога:* {tax_percent}"""
        
        # Добавляем информацию о кредитах
        
        if overdue_steps > 0:
            text += f"\n⚠️ *Просрочено платежей по налогам:* {overdue_steps} ход(ов)"
        if credits and len(credits) > 0:
            text += f"\n\n💳 *Кредиты:* {len(credits)}."
        
        # Добавляем информацию о вкладах
        if deposits and len(deposits) > 0:
            text += f"\n💵 *Вклады:* {len(deposits)}"
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок для страницы банка"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        self.row_width = 2
        # Получаем данные компании для проверки налогов
        company_data = await get_company(id=company_id)
        tax_debt = 0
        if isinstance(company_data, dict):
            tax_debt = company_data.get('tax_debt', 0)
        
        buttons = [
            {
                'text': '💳 Кредит',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'credit'
                )
            },
            {
                'text': '💵 Вклад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'deposit'
                )
            }
        ]
        
        # Добавляем кнопку оплаты налогов, если есть задолженность
        if tax_debt > 0:
            buttons.append({
                'text': f'💸 Оплатить налоги ({tax_debt} 💰)',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'pay_taxes'
                )
            })
        
        self.row_width = 2
        return buttons
    
    @Page.on_callback('credit')
    async def show_credit_page(self, callback: CallbackQuery, args: list):
        """Переход на страницу кредитов"""
        await self.scene.update_page('bank-credit-page')
        await callback.answer()
    
    @Page.on_callback('deposit')
    async def show_deposit_page(self, callback: CallbackQuery, args: list):
        """Переход на страницу вкладов"""
        await self.scene.update_page('bank-deposit-page')
        await callback.answer()
    
    @Page.on_callback('pay_taxes')
    async def pay_taxes_handler(self, callback: CallbackQuery, args: list):
        """Оплата налогов"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            await callback.answer("❌ Ошибка: компания не найдена", show_alert=True)
            return
        
        # Получаем текущий долг
        company_data = await get_company(id=company_id)
        if isinstance(company_data, str):
            await callback.answer(f"❌ Ошибка: {company_data}", show_alert=True)
            return
        
        tax_debt = company_data.get('tax_debt', 0)
        balance = company_data.get('balance', 0)
        
        if tax_debt <= 0:
            await callback.answer("✅ У вас нет налоговой задолженности", show_alert=True)
            return
        
        if balance < tax_debt:
            await callback.answer(
                f"❌ Недостаточно средств!\nНеобходимо: {tax_debt} 💰\nДоступно: {balance} 💰",
                show_alert=True
            )
            return
        
        # Оплачиваем налоги
        result = await company_pay_taxes(company_id=company_id, amount=tax_debt)
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
        else:
            await callback.answer(f"✅ Налоги оплачены: {tax_debt} 💰", show_alert=True)
            # Обновляем страницу
            await self.scene.update_message()
