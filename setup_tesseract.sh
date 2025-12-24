#!/bin/bash

# Script pour installer et configurer Tesseract OCR avec support français

echo "🔧 Configuration de Tesseract OCR..."

# Détecter le système d'exploitation
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 macOS détecté"
    
    # Vérifier si Homebrew est installé
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew n'est pas installé. Installez-le depuis https://brew.sh"
        exit 1
    fi
    
    echo "📦 Installation de Tesseract..."
    brew install tesseract
    
    echo "📦 Installation des données de langue française..."
    brew install tesseract-lang
    
    echo "✅ Tesseract installé avec succès!"
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Linux détecté"
    
    # Détecter la distribution
    if command -v apt-get &> /dev/null; then
        echo "📦 Installation de Tesseract (Ubuntu/Debian)..."
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
        sudo apt-get install -y tesseract-ocr-fra
    elif command -v yum &> /dev/null; then
        echo "📦 Installation de Tesseract (CentOS/RHEL)..."
        sudo yum install -y tesseract
        sudo yum install -y tesseract-langpack-fra
    else
        echo "❌ Distribution Linux non supportée automatiquement"
        echo "Installez Tesseract manuellement pour votre distribution"
        exit 1
    fi
    
    echo "✅ Tesseract installé avec succès!"
    
else
    echo "❌ Système d'exploitation non supporté: $OSTYPE"
    echo "Installez Tesseract manuellement depuis: https://github.com/tesseract-ocr/tesseract"
    exit 1
fi

# Vérifier l'installation
echo ""
echo "🔍 Vérification de l'installation..."
tesseract --version

echo ""
echo "📋 Langues disponibles:"
tesseract --list-langs

echo ""
echo "✅ Configuration terminée!"

