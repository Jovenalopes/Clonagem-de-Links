Link Cloner - Fixes provided

Como usar:
1. Instale dependências: pip install -r requirements.txt
2. Rode: python app.py
3. Acesse: http://localhost:5000/ e gere links
4. O redirecionamento usa HTTP 302 (não usa iframe), evitando bloqueios X-Frame-Options.

Nota:
- Opção de 'mask' (máscara por iframe) foi removida por causar bloqueios em sites que definem X-Frame-Options.
- Se precisar de mascaramento, é necessário implementar proxy HTTP que reescreve respostas — posso ajudar mas é mais complexo.
