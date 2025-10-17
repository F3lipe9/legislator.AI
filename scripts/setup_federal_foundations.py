# scripts/setup_federal_foundations.py
from datasets import load_dataset
import json
import os

def setup_federal_foundations():
    base_dir = "data/federal_foundations"
    os.makedirs(base_dir, exist_ok=True)
    
    print("📥 Setting up federal foundations using Hugging Face datasets...")
    
    try:
        # 1. Load BillSum dataset (perfect for your use case)
        print("📥 Loading BillSum dataset...")
        billsum_dataset = load_dataset("billsum", split='train[:100]')  # First 100 bills to start
        save_billsum_data(billsum_dataset, f"{base_dir}/billsum_congressional.json")
        
        # 2. Try to load Cornell Legal Corpus
        print("📥 Loading legal corpus...")
        try:
            legal_corpus = load_dataset("cornell-legal/legal_corpus", split='train[:500]')
            save_legal_corpus(legal_corpus, f"{base_dir}/cornell_legal_corpus.json")
        except Exception as e:
            print(f"⚠️  Cornell dataset unavailable: {e}")
            # Fallback to other legal datasets
            load_alternative_legal_data(base_dir)
        
        # 3. Create constitutional framework
        create_constitutional_framework(base_dir)
        
        # 4. Create legal principles framework
        create_legal_principles(base_dir)
        
        print("✅ Federal foundations setup complete!")
        print(f"📁 Data saved to: {base_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you installed: pip install datasets")

def save_billsum_data(dataset, filepath):
    """Save BillSum dataset to structured JSON"""
    bills = []
    for item in dataset:
        bills.append({
            "text": item.get('text', ''),
            "summary": item.get('summary', ''),
            "title": item.get('title', ''),
            "bill_id": item.get('bill_id', ''),
            "metadata": {
                "type": "congressional_bill",
                "source": "BillSum",
                "length": len(item.get('text', '')),
                "is_test": item.get('is_test', False)
            }
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(bills, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(bills)} bills from BillSum")

def save_legal_corpus(dataset, filepath):
    """Save legal corpus data"""
    legal_docs = []
    for item in dataset:
        legal_docs.append({
            "text": item.get('text', ''),
            "metadata": {
                "source": item.get('source', 'unknown'),
                "type": item.get('type', 'legal_document'),
                "length": len(item.get('text', '')),
                "jurisdiction": item.get('jurisdiction', 'federal')
            }
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(legal_docs, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(legal_docs)} legal documents")

def load_alternative_legal_data(base_dir):
    """Load alternative legal datasets if Cornell is unavailable"""
    try:
        print("📥 Trying alternative legal datasets...")
        
        # Try Pile of Law dataset
        try:
            pile_of_law = load_dataset("pile-of-law/pile-of-law", "all", split='train[:100]', trust_remote_code=True)
            save_legal_corpus(pile_of_law, f"{base_dir}/pile_of_law_sample.json")
            print("✅ Loaded Pile of Law sample")
        except:
            pass
            
        # Try Harvard Legal Corpus
        try:
            harvard_law = load_dataset("harvard-lil/legal-corpus", split='train[:100]')
            save_legal_corpus(harvard_law, f"{base_dir}/harvard_legal_corpus.json")
            print("✅ Loaded Harvard Legal Corpus sample")
        except:
            pass
            
    except Exception as e:
        print(f"⚠️  Could not load alternative datasets: {e}")

def create_constitutional_framework(base_dir):
    """Create basic constitutional structure"""
    constitution = {
        "document_type": "CONSTITUTIONAL_FRAMEWORK",
        "title": "U.S. Constitutional Principles",
        "principles": [
            {
                "principle": "Separation of Powers",
                "description": "Division of government into three branches",
                "constitutional_basis": "Articles I, II, III",
                "impact": "Checks and balances system",
                "examples": ["Congress makes laws", "President enforces laws", "Courts interpret laws"]
            },
            {
                "principle": "Federalism", 
                "description": "Power division between federal and state governments",
                "constitutional_basis": "10th Amendment",
                "impact": "Dual sovereignty system",
                "examples": ["Federal immigration law", "State education policy"]
            }
        ]
    }
    
    with open(f"{base_dir}/constitutional_principles.json", 'w') as f:
        json.dump(constitution, f, indent=2)
    print("✅ Constitutional framework created!")

def create_legal_principles(base_dir):
    """Create core legal interpretation principles"""
    principles = {
        "document_type": "LEGAL_INTERPRETATION_PRINCIPLES",
        "principles": [
            {
                "principle": "Stare Decisis",
                "definition": "Courts generally follow precedent from previous decisions",
                "application": "Provides stability and predictability in law",
                "importance": "high"
            },
            {
                "principle": "Plain Meaning Rule",
                "definition": "Statutes should be interpreted based on ordinary meaning of words",
                "application": "First step in statutory interpretation",
                "importance": "high"
            }
        ]
    }
    
    with open(f"{base_dir}/legal_interpretation_principles.json", 'w') as f:
        json.dump(principles, f, indent=2)
    print("✅ Legal principles created!")

if __name__ == "__main__":
    setup_federal_foundations()