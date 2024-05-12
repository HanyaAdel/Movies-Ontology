#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Routes for app."""
from functools import partial
from itertools import chain

from bs4 import BeautifulSoup
from flask import render_template, request, flash
import rdflib
from requests import post, codes

from .forms import SPARQLform
from .flask_app import app
from .models import Graph, NAMESPACES
from config import RDF_DIR
from rdflib.namespace import  RDF, RDFS
from rdflib.query import Result
import owlrl
from owlrl import DeductiveClosure
graph = Graph()


@app.template_filter('namespace')
def abbreviate(data):
    if data is None:
        return ""
    for abbr, ns in NAMESPACES.items():
        if str(ns) in data:
            n = data.replace(str(ns), "{}:".format(abbr))
            return '<a href="{url}" title="{n}">{n}</a>'.format(url=data, n=n)
    return data


@app.route("/", methods=["GET"])
def home_page():
    """Render the home page."""
    return render_template("home.html",
                           namespaces=NAMESPACES,
                           form=SPARQLform())

@app.route("/jena1", methods=["GET"])
def jena1():
    person_type_uri = rdflib.URIRef("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/Person")

    results_list = []
    # Iterate through the graph to find all subjects of type Movie
    for subject in graph.subjects(RDF.type, person_type_uri):
        # For each subject that is a movie, find its label (title)
        print("subject:", subject)
        for label in graph.objects(subject, RDFS.label):
            results_list.append((subject, label))
            print("label:", label)
    results = Result('SELECT')
    results.vars = ['person', 'name']  # Define the variable names used in the results
    results.bindings = [{'person': s, 'name': l} for s, l in results_list]
    return show_result(results=results_list, template="jena1.html")

@app.route("/jena2", methods=["GET"])
def jena2():
    query = """prefix : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>  
SELECT ?person_name 
WHERE { 
  ?actor rdf:type :Person. 
  ?actor rdfs:label ?person_name. 
} """
    return run_query(query=query, template="jena2.html")

@app.route("/jena3", methods=["GET"])
def jena3():
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    onto = rdflib.Namespace("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/")
    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)


    persons = set(graph.subjects(RDF.type, onto.Person))

    # Convert set to rdflib.query.Result
    vars = ['person', 'label']  # Define the variables used in the Result
    bindings = []

    for person in persons:
        # Query for the label of each actor
        person_label = list(graph.objects(person, RDFS.label))
        if person_label:
            label = person_label[0]  # Assuming there's at least one label, and taking the first
        else:
            label = "No label found"

        # Add each actor URI and label to the bindings
        bindings.append({'person': person, 'label': label})

    # Create a Result object with SELECT type
    result = Result('SELECT')
    result.vars = vars
    result.bindings = bindings
    
    return show_result(results=result, template="jena3.html")


@app.route("/", methods=["POST"])
def result_page():
    """Render the query result."""
    form = SPARQLform()
    if not form.validate_on_submit():
        errors = chain.from_iterable(
            (
                map(partial("{}. {}".format, field.title()), errs) for
                field, errs in form.errors.items()
            )
        )
        flash("Invalid Query")
        for err in errors:
            flash(err)
        return home_page()
    query = request.form.get('query')
    return run_query(query=query, template="home.html")
    # try:
    #     results = graph.query(query)
    # except Exception as e:
    #     flash("Could not run that query.")
    #     flash("RDFLIB Error: {}".format(e))
    #     sparql_validate(query)
    #     return home_page()
    # return render_template("result.html",
    #                        namespaces=NAMESPACES,
    #                        form=SPARQLform(),
    #                        results=results)

def show_result(results, template):
    return render_template("result.html",
                           base_template=template,
                           namespaces=NAMESPACES,
                           form=SPARQLform(),
                           results=results)

def run_query(query, template):
    try:
        results = graph.query(query)
    except Exception as e:
        flash("Could not run that query.")
        flash("RDFLIB Error: {}".format(e))
        sparql_validate(query)
        return home_page()
    return show_result(results=results, template=template)

def sparql_validate(query):
    prefix = "PREFIX {}: <{}>".format
    prefixes = "\n".join((prefix(ns, uri) for ns, uri in NAMESPACES.items()))
    query = prefixes + "\n\n" + query
    resp = post("http://sparql.org/validate/query", data=dict(query=query))
    if resp.status_code == codes.ok:
        soup = BeautifulSoup(resp.content.decode('utf-8'), "html.parser")
        pres = soup.find_all('pre')
        for p in pres:
            flash(p)
    else:
        flash("Unable to access query validation service.")
