# Handlers

Solo enrutan eventos desde Telegram. **SIN lógica de negocio, SIN acceso a DB.**

## Estructura

<!-- AUTO:STRUCTURE -->
```
handlers/
├── common_handlers.py
├── admin_handlers.py  [AdminStates(waiting_channel_message, waiting_tariff_name, waiting_tariff_days, waiting_tariff_price, waiting_custom_wait_time)]
├── channel_handlers.py  [ChannelStates(waiting_channel_message, confirming_channel, selecting_channel_type, configuring_wait_time, configuring_invite_link)]
├── vip_handlers.py  [TariffStates(waiting_name, waiting_days, waiting_price, confirming), TokenStates(selecting_tariff)]
├── free_channel_handlers.py
├── gamification_user_handlers.py  # Gamificacion
├── gamification_admin_handlers.py  [EmojiConfigStates(waiting_emoji, waiting_name, waiting_value), DailyGiftConfigStates(waiting_amount)]  # Gamificacion
├── broadcast_handlers.py  [BroadcastStates(selecting_channel, waiting_text, waiting_attachment_decision, waiting_attachment, waiting_reaction_decision, selecting_reactions, waiting_protection_decision, confirming)]  # Gamificacion
├── package_handlers.py  [PackageWizardStates(waiting_name, waiting_description, waiting_files, waiting_store_stock, waiting_reward_stock, confirming), SendPackageStates(selecting_package, waiting_user_id, confirming), UpdatePackageStates(selecting_package, waiting_files, confirming), DeleteFileStates(selecting_package, deleting_files)]  # Paquetes
├── mission_user_handlers.py  # Misiones y Recompensas
├── mission_admin_handlers.py  [MissionWizardStates(waiting_name, waiting_description, selecting_type, waiting_target, selecting_frequency, selecting_reward, confirming), RewardWizardStates(waiting_name, waiting_description, selecting_type, waiting_besito_amount, selecting_package, create_package_requested, selecting_tariff, confirming)]  # Misiones y Recompensas
├── reward_admin_handlers.py  [RewardWizardStates(waiting_name, waiting_description, selecting_type, waiting_besito_amount, selecting_package, create_package_requested, selecting_tariff, confirming), PackageFromRewardStates(waiting_name, waiting_description, waiting_files, waiting_store_stock, waiting_reward_stock, confirming)]  # Misiones y Recompensas
├── reward_user_handlers.py  # Misiones y Recompensas
├── store_user_handlers.py  [SearchStates(waiting_query)]  # Tienda
├── store_admin_handlers.py  [ProductWizardStates(waiting_name, waiting_description, selecting_package, waiting_price, waiting_stock, confirming), ProductRestockStates(waiting_amount, waiting_threshold), ProductEditStates(selecting_field, waiting_name, waiting_description, selecting_package, waiting_price, waiting_stock_value, confirming)]  # Tienda
├── promotion_user_handlers.py  # Promociones
├── promotion_admin_handlers.py  [PromotionWizardStates(waiting_name, waiting_description, selecting_source, selecting_package, waiting_manual_files, waiting_price, waiting_dates, waiting_question_set, confirming), BlockUserStates(waiting_reason, confirming)]  # Promociones
├── story_user_handlers.py  [ArchetypeQuizStates(answering)]  # Narrativa
├── story_admin_handlers.py  [NodeWizardStates(waiting_title, waiting_content, selecting_type, waiting_chapter, waiting_requirements, waiting_cost, confirming), ChoiceWizardStates(selecting_node, waiting_text, selecting_next_node, waiting_archetype_points, confirming), ArchetypeWizardStates(selecting_type, waiting_name, waiting_description, waiting_welcome, confirming), AchievementWizardStates(waiting_name, waiting_description, waiting_icon, confirming)]  # Narrativa
├── analytics_handlers.py  # Analytics
├── vip_user_handlers.py  [AnonymousMessageStates(waiting_message, confirming_send)]  # Mensajes Anónimos VIP
├── anonymous_message_admin_handlers.py  [AnonymousReplyStates(waiting_reply)]  # Mensajes Anónimos VIP
├── game_user_handlers.py  [TriviaStreakStates(waiting_streak_choice, streak_continue)]  # Minijuegos
├── trivia_discount_admin_handlers.py  [TriviaDiscountStates(waiting_promotion_type, waiting_promotion, waiting_custom_description, waiting_discount_percentage, waiting_required_streak, waiting_tier_mode, waiting_discount_tiers, waiting_max_codes, waiting_start_date, waiting_end_date, waiting_duration, waiting_auto_reset, waiting_reset_cycles, waiting_question_set, waiting_confirmation, waiting_extend_duration)]  # Trivia Discount
├── question_set_admin_handlers.py  [QuestionSetStates(waiting_name, waiting_description, waiting_file_path, waiting_question_set_confirm, waiting_set_to_activate)]  # Question Sets
├── trivia_admin_handlers.py  [TriviaConfigStates(waiting_free_limit, waiting_vip_limit, waiting_vip_exclusive_limit)]  # Trivia Management
```



## Reglas de Handlers

1. **UN service** por handler
2. **SIN lógica** de negocio
3. **SIN acceso** directo a DB
4. **Logging** de eventos recibidos

## Ejemplo Correcto

`async def handle_besitos_balance(callback: CallbackQuery, service: BesitoService):
    """Solo llama al service, no tiene lógica."""
    user_id = callback.from_user.id
    balance = await service.get_balance(user_id)
    await callback.message.edit_text(f"Tu saldo: {balance}")`

## Ejemplo Incorrecto (PROHIBIDO)

`async def handle_besitos_balance(callback: CallbackQuery):
    # ❌ Lógica en handler
    user = await session.get(User, callback.from_user.id)
    user.besitos += 10  # ❌ Lógica de negocio
    await session.commit()  # ❌ Acceso a DB`
