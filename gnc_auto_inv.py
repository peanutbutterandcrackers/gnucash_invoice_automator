import csv
import gnucash
from decimal import Decimal
from dateutil.parser import parse as parse_date
from gnucash import gnucash_business, GncNumeric

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
GNCSession = gnucash.Session(GNCFile)
GNCBook = GNCSession.book
GNCRootAc = GNCBook.get_root_account()
NPR = GNCBook.get_table().lookup('CURRENCY', 'NPR')
IncomeAccount = GNCRootAc.lookup_by_name("Income").lookup_by_name("Sales").lookup_by_name("Milk Sales")
ReceivableAC = GNCRootAc.lookup_by_name("Assets").lookup_by_name("Accounts Receivable")
# open_gnucash_file()
# This function should take care of creating backups, just in case.
# If anything goes wrong, revert the changes, even, perhaps.

ZERO_VALUES = [0, '', '0', None]

for record in CSVReader:
		PostDate = DueDate = parse_date(record['Date'])
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

		# DEBUG:
		#import sys
		#print("GNCBook %s" % type(GNCBook))
		#print("NPR %s" % type(NPR))
		#print("GNCCustomer %s" % type(GNCCustomer))
		#print("ReceivableAC %s" % type(ReceivableAC), ReceivableAC)
		#print("IncomeAccount %s" % type(IncomeAccount), IncomeAccount)
		#GNCSession.save()
		#GNCSession.end()
		#sys.exit(0)

		if quantity not in ZERO_VALUES: # make something akin to row_is_valid_record()
				Invoice = gnucash_business.Invoice(GNCBook, GNCBook.InvoiceNextID(GNCCustomer), NPR, GNCCustomer)

				# try catching "Remarks" or "Description" column and if they aren't there then generate one
				Description = "%s Ltr. Milk" % quantity
				InvoiceValue = gnc_numeric_from_decimal(Decimal(unitPrice)) # Unit Price

				InvoiceEntry = gnucash_business.Entry(GNCBook, Invoice)
				InvoiceEntry.SetDescription(Description)
				InvoiceEntry.SetQuantity(gnc_numeric_from_decimal(Decimal(quantity)))
				InvoiceEntry.SetInvAccount(IncomeAccount)
				InvoiceEntry.SetInvPrice(InvoiceValue)

				# Debug:
				# print(PostDate, DueDate)

				AccumulateSplits = True
				Autopay = False 
				Invoice.PostToAccount(ReceivableAC, PostDate, DueDate, Description, AccumulateSplits, Autopay)
				#create_invoice()
		
				if customerHasPaid:
						PaymentTransaction = None 
						TransferAccount = GNCRootAc.lookup_by_name("Assets").lookup_by_name("Current Assets").lookup_by_name("Petty Cash")
						AmountPaid = gnc_numeric_from_decimal(Decimal(PaidAmount))
						Changes_Refunds = gnc_numeric_from_decimal(Decimal(0))
						PaymentDate = PostDate
						Memo = "Payment Received"
						Num = ""
						Invoice.ApplyPayment(PaymentTransaction, TransferAccount, AmountPaid, Changes_Refunds, PaymentDate, Memo, Num)
						#process_payment()

GNCSession.save()
GNCSession.end()

### THE FOLLOWING MIGHT GO TO ANOTHER MODULE
def create_invoice():
	pass

