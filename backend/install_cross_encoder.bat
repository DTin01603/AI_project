@echo off
REM Script to install cross-encoder dependencies for Windows

echo Installing sentence-transformers for cross-encoder support...
pip install sentence-transformers

echo.
echo Testing cross-encoder installation...
python -c "from sentence_transformers import CrossEncoder; print('✓ CrossEncoder available'); model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); print('✓ Model loaded successfully'); score = model.predict([['test query', 'test document']]); print(f'✓ Prediction works: score={score[0]:.3f}')"

echo.
echo ✓ Cross-encoder installation complete!
echo.
echo To use cross-encoder in your RAG system:
echo   1. Set RAG_ENABLE_RERANKING=true in your .env
echo   2. Restart your application
echo.
pause
