from oms import Page
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_company, company_pay_credit
from oms.utils import callback_generator


class BankCreditPay(Page):
    """Страница оплаты кредита"""
    
    __page_name__ = "bank-credit-pay"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        pay_credit_index = scene_data.get('pay_credit_index', 0)
        error = scene_data.get('error_message', '')
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        credits = company_data.get('credits', [])
        balance = company_data.get('balance', 0)
        
        if pay_credit_index >= len(credits):
            return "❌ Ошибка: кредит не найден"
        
        credit = credits[pay_credit_index]
        total = credit.get("total_to_pay", 0)
        paid = credit.get("paid", 0)
        need_pay = credit.get("need_pay", 0)
        remaining = total - paid
        
        text = f"""💸 *Оплата кредита #{pay_credit_index + 1}*

*Информация о кредите:*
Осталось выплатить: {remaining:,} 💰
Текущий платеж: {need_pay:,} 💰
Ваш баланс: {balance:,} 💰

*Введите сумму для оплаты:*

Минимум: {need_pay:,} 💰 (текущий платеж)
Максимум: {remaining:,} 💰 (весь остаток)""".replace(",", " ")
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        self.row_width = 2
        return [
            {
                'text': '❌ Отменить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel'
                )
            }
        ]
    
    @Page.on_callback('cancel')
    async def cancel_handler(self, callback: CallbackQuery, args: list):
        """Отмена оплаты кредита"""
        scene_data = self.scene.get_data('scene')
        scene_data['pay_credit_index'] = 0
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-main')
        await callback.answer("❌ Операция отменена")
    
    @Page.on_text('int')
    async def handle_pay_input(self, message: Message, value: int):
        """Обработка ввода суммы оплаты"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        pay_credit_index = scene_data.get('pay_credit_index', 0)
        
        # Очищаем предыдущую ошибку
        scene_data['error_message'] = ''
        
        # Получаем данные для проверки
        company_data = await get_company(id=company_id)
        if isinstance(company_data, str):
            scene_data['error_message'] = f'Ошибка: {company_data}'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        credits = company_data.get('credits', [])
        balance = company_data.get('balance', 0)
        
        if pay_credit_index >= len(credits):
            scene_data['error_message'] = 'Ошибка: кредит не найден'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        credit = credits[pay_credit_index]
        total = credit.get("total_to_pay", 0)
        paid = credit.get("paid", 0)
        need_pay = credit.get("need_pay", 0)
        remaining = total - paid
        
        # Проверяем минимальную сумму (текущий платеж)
        if value < need_pay:
            scene_data['error_message'] = f'Минимальная сумма оплаты: {need_pay:,} 💰 (текущий платеж)'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Проверяем, что сумма не превышает остаток
        if value > remaining:
            scene_data['error_message'] = f'Сумма превышает остаток по кредиту! Осталось выплатить: {remaining:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Проверяем баланс
        if value > balance:
            scene_data['error_message'] = f'Недостаточно средств! Необходимо: {value:,} 💰, Доступно: {balance:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Оплачиваем кредит
        result = await company_pay_credit(
            company_id=company_id,
            credit_index=pay_credit_index,
            amount=value
        )
        
        if isinstance(result, str):
            scene_data['error_message'] = f'Ошибка: {result}'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        else:
            # Успешная оплата - показываем уведомление и возвращаемся к главному экрану
            scene_data['pay_credit_index'] = 0
            scene_data['error_message'] = ''
            scene_data['success_message'] = f'Платеж выполнен: {value:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_page('bank-credit-main')
