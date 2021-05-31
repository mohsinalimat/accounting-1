# Copyright (c) 2021, ac and contributors
# For license information, please see license.txt
import frappe
from accounting.accounting.doctype.gl_entry.utils import create_gl_entry, create_revere_gl_entry
from frappe.model.document import Document
from frappe.utils import flt
from tests.utils import get_or_create_doc


class SalesInvoice(Document):
	def validate(self):
		self.pre_fill()

	def on_submit(self):
		create_gl_entry(self, self.debit_to, self.total_amount, 0)
		create_gl_entry(self, self.income_account, 0, self.total_amount)

	def on_cancel(self):
		self.ignore_linked_doctypes = ('GL Entry',)
		create_revere_gl_entry(self.doctype, self.name)

	def pre_fill(self):
		self.total_quantity, self.total_amount = 0.0, 0.0
		for item in self.items:
			item.update({'amount': flt(item.rate) * flt(item.quantity)})
			self.total_quantity += flt(item.quantity)
			self.total_amount += flt(item.amount)
			print(self.total_amount)

		# self.save()

	def add_item(self, new_item, quantity=1):
		if not self.items:
			self.set('items', [{'item': new_item.name, 'quantity': quantity}])
			self.save()
			return

		new_item_added = False

		for item in self.items:
			if item.item == new_item.name:
				item.update({'quantity': flt(quantity) + flt(item.quantity)})
				new_item_added = True
				break

		if not new_item_added:
			self.append('items', {'item': new_item.name, 'quantity': quantity})

		print('------')
		print(self.total_amount)
		self.pre_fill()
		self.save()


@frappe.whitelist(allow_guest=True)
def add_to_cart(username, item_name):
	item = frappe.get_doc('Item', item_name)

	# item = frappe.get_value('Item', {'item_name': item_name}, ['name', 'item_code'])
	user = frappe.get_value('User', {'name': username}, ['name', 'email'], as_dict=1)

	_, party = get_or_create_doc('Party', user['name'])

	try:
		invoice = frappe.get_list('Sales Invoice', filters={
			'party': party.party_name,
			'docstatus': 0,
		})[0]
		_, invoice = get_or_create_doc('Sales Invoice', invoice['name'])
	except IndexError:
		invoice = frappe.new_doc('Sales Invoice')
		invoice.party = party.party_name
		invoice.insert()
		_, invoice = get_or_create_doc('Sales Invoice', invoice.name)

	invoice.add_item(item)


@frappe.whitelist(allow_guest=True)
def buy_now(invoice_name):
	invoice = frappe.get_doc('Sales Invoice', invoice_name)
	invoice.submit()
