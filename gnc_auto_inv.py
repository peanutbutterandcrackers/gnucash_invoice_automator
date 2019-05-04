import csv
import gnucash
import argparse

from decimal import Decimal
from dateutil.parser import parse as parse_date
from gnucash import gnucash_business, GncNumeric

class Record(dict):
	"""
		A Record, as-in transaction record. A row from a spreadsheet recording
		a transaction. In this case, a row from a csv file. Each record, here,
		is a dictionary of each row in the csv file, with the column headers
		as the keys to the corresponding values from the row.
		Example Record:
			{
			 "Customer": "John Doe",
		 	 "Customer ID": "000001",
			 "Quanitity": "3",
			 "Unit Price": "80"
			 }

		This subclass of Python's default dict only makes the following extension:
		If a key does not exist, instead of raising a KeyError, this returns an
		empty string. This will, hopefully, allow the script to be a lot more flexible.
	"""

	def __getitem__(self, key):
		try:
			return dict.__getitem__(self, key)
		except KeyError:
			return ''

def isEmptyValue(val):
	"""Given a value, test whether or not it is zero or empty"""
	ZERO_VALUES = [0, '', '0', None] # Zero/Empty
	return val in ZERO_VALUES

def getDefaultCurrency():
	"""Return the system default currency"""
	import locale
	locale.setlocale(locale.LC_ALL, "")
	return locale.localeconv()['int_curr_symbol'].strip()

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
	shutil.copy2(filePath, backupPath)

def open_and_unpack_record_csv(csvfile, fieldDelimiter='\t'):
	"""Given the path to a csv file containing the transaction records, return a csv.DictReader object"""
	CSVFile = open(csvfile, 'r')
	return csv.DictReader(CSVFile, delimiter=fieldDelimiter)

def open_gnucash_file(gnucashfile):
	"""Open the given GNUCash file (after making it's backup in the same dir) and return gnucash.Session object"""
	create_backup(gnucashfile)
	return gnucash.Session(gnucashfile)

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
	# IncomeAccount = GNCRootAC.lookup_by_name("Income").lookup_by_name("Sales").lookup_by_name("Milk Sales")
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

def main():
	parser = argparse.ArgumentParser(
		description="A script to automatically add Invoice and Payments to a GNUCash file from a CSV file (exported from LibreOffice Calc) containing the trasaction records."
	  )
	parser.add_argument("CSVFILE", help="The CSV file that contains the transaction records")
	parser.add_argument("GNUCASHFILE", help="The GNUCash file to record the transactions in")
	args = parser.parse_args()

	TRANSACTION_RECORDS = open_and_unpack_record_csv(args.CSVFILE)
	GNCSession = open_gnucash_file(args.GNUCash)
	
	GNCBook = GNCSession.book
	GNCRootAC = GNCBook.get_root_account()
	ReceivableAC = gnc_get_account_by_name(GNCRootAC, "Assets:Accounts Receivable") # Hard-coding this as it is the norm

	for TransactionRecord in TRANSACTION_RECORDS:
			# Change TransactionRecord's type from dict to Record
			TransactionRecord = Record(TransactionRecord)
	
			##### START EXTRACTING INFO FROM THE RECORD #####
			# STANDARD MAPPINGS
			CustomerID = TransactionRecord['Customer ID']
			if isEmptyValue(CustomerID):
					continue
			Date = parse_date(TransactionRecord['Date'])
			PostDate = DueDate = Date # For now, anyways
			Quantity = TransactionRecord['Quantity']
			UnitPrice = TransactionRecord['Unit Price']
			Description = TransactionRecord['Description']
			Currency = TransactionRecord['Currency']
			# Note: Define 'global' vars, if IncomeAccount has been defined there, do not extract from
			# TransactionRecord. If not, extract from here. If it is an empty value, fall back to "Income:Sales"
			IncomeAccount = TransactionRecord['Income Account']
			# NON-STANDARD MAPPINGS
			Remarks = TransactionRecord['Remarks']

			# CUSTOM VARIABLES
			CustomDescription = "%s Ltr. Milk" % Quantity

			# FILTERING/FUTHER-MODIFYING THE VARIABLES
			Description = Description if not isEmptyValue(Description) else CustomDescription
			if not isEmptyValue(Remarks):
					Description += " (%s)" % Remarks
			Currency = Currency if not isEmptyValue(Currency) else getDefaultCurrency()
			IncomeAccount = IncomeAccount if not isEmptyValue(IncomeAccount) else "Income:Sales"
	
			GNCIncomeAccount = gnc_get_account_by_name(GNCRootAC, IncomeAccount)
			GNCCurrency = GNCBook.get_table().lookup('CURRENCY', Currency)
			GNCCustomer = GNCBook.CustomerLookupByID(CustomerID)
			if (GNCCustomer == None) or (not isinstance(GNCCustomer, gnucash_business.Customer)):
					continue # use logger here (and in rest of the code)
	
			customerHasPaid = False
			if not isEmptyValue(TransactionRecord['Cash Paid']):
				customerHasPaid = True
				PaidAmount = TransactionRecord['Cash Paid']
	
			if not isEmptyValue(Quantity): # make something akin to row_is_valid_record()
					Invoice = gnucash_business.Invoice(GNCBook, GNCBook.InvoiceNextID(GNCCustomer), GNCCurrency, GNCCustomer)
					InvoiceValue = gnc_numeric_from_decimal(Decimal(UnitPrice)) # Unit Price
					InvoiceEntry = gnucash_business.Entry(GNCBook, Invoice)
					InvoiceEntry.SetDateEntered(PostDate)
					InvoiceEntry.SetDescription(Description)
					InvoiceEntry.SetQuantity(gnc_numeric_from_decimal(Decimal(Quantity)))
					InvoiceEntry.SetInvAccount(GNCIncomeAccount)
					InvoiceEntry.SetInvPrice(InvoiceValue)
					AccumulateSplits = True
					Autopay = True
					Invoice.PostToAccount(ReceivableAC, PostDate, DueDate, Description, AccumulateSplits, Autopay)
			
			if customerHasPaid:
					# (Ref: https://code.gnucash.org/docs/MAINT/group__Owner.html#ga66a4b67de8ecc7798bd62e34370698fc)
					Transaction = None
					GList = None
					PostedAccount = ReceivableAC
					TransferAccount = gnc_get_account_by_name(GNCRootAC, "Assets:Current Assets:Petty Cash")
					AmountPaid = gnc_numeric_from_decimal(Decimal(PaidAmount))
					Refund = gnc_numeric_from_decimal(Decimal(0))
					PaymentDate = Date
					Memo = "Payment Received"
					Num = ""
					AutoPay = True
					GNCCustomer.ApplyPayment(Transaction, GList, PostedAccount, TransferAccount, AmountPaid, Refund, PaymentDate, Memo, Num, AutoPay) 
	
	GNCSession.save()
	GNCSession.end()

if __name__ == "__main__":
	main()
