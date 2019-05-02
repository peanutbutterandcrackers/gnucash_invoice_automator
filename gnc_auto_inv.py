import csv
import gnucash
from decimal import Decimal
from dateutil.parser import parse as parse_date
from gnucash import gnucash_business, GncNumeric

def create_backup(_file):
	"""Makes a backup of the given file in the same directory"""
	import sys
	import datetime
	import os, shutil
	SCRIPT_NAME = os.path.splitext(sys.argv[0])[0]
	filePath = os.path.abspath(_file)
	dirName = os.path.dirname(filePath)
	fileName = os.path.basename(_file)
	timeStamp = datetime.datetime.now().isoformat()
	backupFileName = "%s.%s.%s.backup.gnucash" % (fileName, SCRIPT_NAME, timeStamp)
	backupPath = dirName + os.sep + backupFileName
	shutil.copyfile(filePath, backupPath)

def gnc_get_account_by_name(rootAccount, accountString):
	"""Given the rootAccount of a GNCBook and an accountString in the form that appears
		in the GNUCash GUI under "Transfer" column of each account, returns the account.
		Example account strings:
			"Assets:Current Assets:Petty Cash"
			"Assets:Accounts Receivable"
			"Assets:Checking Account"
		[rootAccount is gotten thus: gnucash.Session("foobar.gnucash").book.get_root_account()]
	"""
	# Previously, accounts were gotten thus:
	# IncomeAccount = GNCRootAc.lookup_by_name("Income").lookup_by_name("Sales").lookup_by_name("Milk Sales")
	# This function recursively deals with nested accounts. Thereby eliminating the need for hard-coded accounts.
	accountNesting = accountString.split(":")
	if len(accountNesting) == 1:
			return rootAccount.lookup_by_name(accountNesting[0])
	else:
			return gnc_get_account_by_name(rootAccount.lookup_by_name(accountNesting[0]), ":".join(accountNesting[1:]))

# The following function was copied from https://github.com/Gnucash/gnucash/blob/master/bindings/python/example_scripts/simple_invoice_insert.py
def gnc_numeric_from_decimal(decimal_value):
    sign, digits, exponent = decimal_value.as_tuple()

    # convert decimal digits to a fractional numerator
    # equivlent to
    # numerator = int(''.join(digits))
    # but without the wated conversion to string and back,
    # this is probably the same algorithm int() uses
    numerator = 0
    TEN = int(Decimal(0).radix()) # this is always 10
    numerator_place_value = 1
    # add each digit to the final value multiplied by the place value
    # from least significant to most sigificant
    for i in range(len(digits)-1,-1,-1):
        numerator += digits[i] * numerator_place_value
        numerator_place_value *= TEN

    if decimal_value.is_signed():
        numerator = -numerator

    # if the exponent is negative, we use it to set the denominator
    if exponent < 0 :
        denominator = TEN ** (-exponent)
    # if the exponent isn't negative, we bump up the numerator
    # and set the denominator to 1
    else:
        numerator *= TEN ** exponent
        denominator = 1

    return GncNumeric(numerator, denominator)

CSV_FILE = "asdf.csv"
DELIMITER = "\t"
CSVFile = open(CSV_FILE, 'r')
CSVReader = csv.DictReader(CSVFile, delimiter=DELIMITER)

GNCFile = "foobar.gnucash"
create_backup(GNCFile)
GNCSession = gnucash.Session(GNCFile)
GNCBook = GNCSession.book
GNCRootAc = GNCBook.get_root_account()
NPR = GNCBook.get_table().lookup('CURRENCY', 'NPR')
IncomeAccount = gnc_get_account_by_name(GNCRootAc, "Income:Sales:Milk Sales")
ReceivableAC = gnc_get_account_by_name(GNCRootAc, "Assets:Accounts Receivable")
# open_gnucash_file()
# This function should take care of creating backups, just in case.
# If anything goes wrong, revert the changes, even, perhaps.

ZERO_VALUES = [0, '', '0', None]

for record in CSVReader:
		Date = parse_date(record['Date'])
		PostDate = DueDate = Date
		customerID = record['Customer ID']
		quantity = record['Quantity']
		unitPrice = record['Unit Price']
		customerHasPaid = False
		if record['Cash Paid'] not in ZERO_VALUES:
			customerHasPaid = True
			PaidAmount = record['Cash Paid']

		if customerID in ZERO_VALUES: # Replace this with is_proper_customer_id()
				continue
		GNCCustomer = GNCBook.CustomerLookupByID(customerID)
		if (GNCCustomer == None) or (not isinstance(GNCCustomer, gnucash_business.Customer)):
				continue # use logger here (and in rest of the code)

		if quantity not in ZERO_VALUES: # make something akin to row_is_valid_record()
				Invoice = gnucash_business.Invoice(GNCBook, GNCBook.InvoiceNextID(GNCCustomer), NPR, GNCCustomer)
				# try catching "Remarks" or "Description" column and if they aren't there then generate one
				Description = "%s Ltr. Milk" % quantity
				InvoiceValue = gnc_numeric_from_decimal(Decimal(unitPrice)) # Unit Price
				InvoiceEntry = gnucash_business.Entry(GNCBook, Invoice)
				InvoiceEntry.SetDateEntered(PostDate)
				InvoiceEntry.SetDescription(Description)
				InvoiceEntry.SetQuantity(gnc_numeric_from_decimal(Decimal(quantity)))
				InvoiceEntry.SetInvAccount(IncomeAccount)
				InvoiceEntry.SetInvPrice(InvoiceValue)
				AccumulateSplits = True
				Autopay = True
				Invoice.PostToAccount(ReceivableAC, PostDate, DueDate, Description, AccumulateSplits, Autopay)
		
		if customerHasPaid:
				# (Ref: https://code.gnucash.org/docs/MAINT/group__Owner.html#ga66a4b67de8ecc7798bd62e34370698fc)
				Transaction = None
				GList = None
				PostedAccount = ReceivableAC
				TransferAccount = gnc_get_account_by_name(GNCRootAc, "Assets:Current Assets:Petty Cash")
				AmountPaid = gnc_numeric_from_decimal(Decimal(PaidAmount))
				Refund = gnc_numeric_from_decimal(Decimal(0))
				PaymentDate = Date
				Memo = "Payment Received"
				Num = ""
				AutoPay = True
				GNCCustomer.ApplyPayment(Transaction, GList, PostedAccount, TransferAccount, AmountPaid, Refund, PaymentDate, Memo, Num, AutoPay) 

GNCSession.save()
GNCSession.end()
