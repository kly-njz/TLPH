from firebase_config import get_firestore_db, initialize_firebase_admin


def main():
    initialize_firebase_admin()
    db = get_firestore_db()
    print("All expense_categories documents:")
    docs = db.collection("expense_categories").stream()
    count = 0
    for doc in docs:
        data = doc.to_dict()
        print(f"ID: {doc.id}")
        print(f"  name: {data.get('name')}")
        print(f"  municipality: {data.get('municipality')}")
        print(f"  coa_code: {data.get('coa_code')}")
        print(f"  expense_type: {data.get('expense_type')}")
        print(f"  office: {data.get('office')}")
        print(f"  fund_type: {data.get('fund_type')}")
        print(f"  status: {data.get('status')}")
        print(f"  tax_rate: {data.get('tax_rate')}")
        print("---")
        count += 1
    print(f"Total: {count} documents.")

if __name__ == "__main__":
    main()
