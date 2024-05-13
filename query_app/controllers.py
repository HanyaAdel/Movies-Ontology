#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Routes for app."""
from functools import partial
from itertools import chain

from bs4 import BeautifulSoup
from flask import render_template, request, flash
import rdflib
import rdflib.term
from requests import post, codes

from .forms import SPARQLform , Movieform
from .flask_app import app
from .models import Graph, NAMESPACES
from config import RDF_DIR
from rdflib.namespace import  RDF, RDFS
from rdflib.query import Result
from rdflib import OWL
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
  ?person rdf:type :Person. 
  ?person rdfs:label ?person_name. 
} """
    return run_query(query=query, template="jena2.html")

@app.route("/jena3", methods=["GET"])
def jena3():
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    onto = rdflib.Namespace("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/")
    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)


    persons = set(graph.subjects(RDF.type, onto.Person))

    # Convert set to rdflib.query.Result
    vars = ['person', 'name']  # Define the variables used in the Result
    bindings = []

    for person in persons:
        # Query for the label of each actor
        person_label = list(graph.objects(person, RDFS.label))
        if person_label:
            label = person_label[0]  # Assuming there's at least one label, and taking the first
        else:
            label = "No label found"

        # Add each actor URI and label to the bindings
        bindings.append({'person': person, 'name': label})

    # Create a Result object with SELECT type
    result = Result('SELECT')
    result.vars = vars
    result.bindings = bindings

    return show_result(results=result, template="jena3.html")

@app.route("/jena6_1", methods=["GET"])
def jena6_1():
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    onto = rdflib.Namespace("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/")

    # Rule 1: ActorDirector
    graph.add((onto.ActorDirector, RDF.type, OWL.Class))
    graph.add((onto.ActorDirector, RDFS.subClassOf, onto.Person))

    # Create a blank node for intersection and ensure the intersection is properly constructed
    intersection = rdflib.BNode()
    list_actor = rdflib.BNode()
    list_director = rdflib.BNode()

    graph.add((intersection, RDF.type, OWL.Class))
    graph.add((intersection, OWL.intersectionOf, list_actor))
    graph.add((list_actor, RDF.first, onto.Actor))
    graph.add((list_actor, RDF.rest, list_director))
    graph.add((list_director, RDF.first, onto.Director))
    graph.add((list_director, RDF.rest, RDF.nil))

    graph.add((onto.ActorDirector, OWL.equivalentClass, intersection))

    # Apply reasoning
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, datatype_axioms=False).expand(graph)

    query = """prefix : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>  
SELECT ?person_name 
WHERE { 
  ?person rdf:type :ActorDirector. 
  ?person rdfs:label ?person_name. 
} """
    return run_query(query=query, template="jena6_1.html")

@app.route("/jena6_2", methods=["GET"])
def jena6_2():
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    onto = rdflib.Namespace("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/")

    #Rule 2: MultiGenreMovies
    graph.add((onto.hasMultipleGenres, RDF.type, OWL.DatatypeProperty))
    graph.add((onto.MultiGenreMovies, RDF.type, OWL.Class))
    graph.add((onto.MultiGenreMovies, RDFS.subClassOf, onto.Movie))
    graph.add((onto.MultiGenreMovies, OWL.equivalentClass, rdflib.BNode()))
    graph.add((onto.MultiGenreMovies, RDF.type, OWL.Restriction))
    graph.add((onto.MultiGenreMovies, OWL.onProperty, onto.hasMultipleGenres))
    graph.add((onto.MultiGenreMovies, OWL.hasValue, rdflib.Literal(True)))

        # Preprocess and mark multi-genre movies
    for movie in graph.subjects(RDF.type, onto.Movie):
        genres = set(graph.objects(movie, onto.hasGenre))
        if len(genres) > 1:
            graph.add((movie, onto.hasMultipleGenres, rdflib.Literal(True)))

    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    query = """prefix : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>  
SELECT ?movie_name 
WHERE { 
  ?movie rdf:type :MultiGenreMovies. 
  ?movie rdfs:label ?movie_name. 
} """
    return run_query(query=query, template="jena6_2.html")

@app.route("/jena6_3", methods=["GET"])
def jena6_3():
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    onto = rdflib.Namespace("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/")

    #Rule 3: Old Movies
    graph.add((onto.isOld, RDF.type, OWL.DatatypeProperty))
    graph.add((onto.OldMovies, RDF.type, OWL.Class))
    graph.add((onto.OldMovies, RDFS.subClassOf, onto.Movie))
    graph.add((onto.OldMovies, OWL.equivalentClass, rdflib.BNode()))
    graph.add((onto.OldMovies, RDF.type, OWL.Restriction))
    graph.add((onto.OldMovies, OWL.onProperty, onto.isOld))
    graph.add((onto.OldMovies, OWL.hasValue, rdflib.Literal(True)))

    # Process each movie and check its release year
    for movie in graph.subjects(RDF.type, onto.Movie):
        release_year = graph.value(movie, onto.Year)
        if release_year and int(release_year) < 2000:
            graph.add((movie, onto.isOld, rdflib.Literal(True)))
        else:
            graph.add((movie, onto.isOld, rdflib.Literal(False)))

    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    query = """prefix : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>  
SELECT ?movie_name 
WHERE { 
  ?movie rdf:type :OldMovies. 
  ?movie rdfs:label ?movie_name. 
} """
    return run_query(query=query, template="jena6_3.html")

    


@app.route("/jena4", methods=["GET"])
def jena4():
    """Render the jena4 page."""
    return render_template("jena4.html",
                           namespaces=NAMESPACES,
                           form=Movieform())

@app.route("/jena4", methods=["POST"])
def movie_page():
    """Render the query result."""
    form = Movieform()
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
        return jena4()
    
    movie = request.form.get('movie')
        
    query = f"""PREFIX : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>

    SELECT ?year ?country (GROUP_CONCAT(DISTINCT ?genre_name; SEPARATOR=", ") AS ?genres) (GROUP_CONCAT(DISTINCT ?actor_name; SEPARATOR=", ") AS ?actors)
    WHERE {{
      ?movie rdf:type :Movie.
      ?movie rdfs:label "{movie}".
      OPTIONAL {{ ?movie :Year ?year .}}
      OPTIONAL {{ ?movie :Country ?country }}
      OPTIONAL {{ ?movie :hasGenre ?genre }}
      OPTIONAL {{ ?actor :isActorOf ?movie }}
      OPTIONAL {{ ?genre rdfs:label ?genre_name }}
      OPTIONAL {{ ?actor rdfs:label ?actor_name }}
    }}"""

    try:
        results = graph.query(query)
        if any(binding["genres"].value == "" for binding in results.bindings):
            flash(f"No information found for the movie '{movie}'")
            return jena4()
    except Exception as e:
        flash("Could not run that query.")
        flash("RDFLIB Error: {}".format(e))
        sparql_validate(query)
        return jena4()
    
    return render_template("result.html",
                        base_template="jena4.html", 
                        namespaces=NAMESPACES,
                        form=Movieform(),
                        results=results)

@app.route("/jena5", methods=["GET"])
def jena5():

    global graph

    # Load the OWL rule file
    rule_file = "rdf/rules.ttl"
    rule_graph = Graph()
    rule_graph.parse(rule_file, format="ttl")

    # Print the content of the rule graph before merging
    print("Rule Graph Content Before Merging:")
    print(rule_graph.serialize(format="turtle"))

    # Merge the rule graph with the main graph
    graph = graph + rule_graph

    # Apply OWL reasoning
    owlrl.OWLRL_Semantics(graph, axioms=True, daxioms=True)
    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    # Query to find individuals who are both actors and directors
    query = """
    PREFIX : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>
    SELECT DISTINCT ?person_name
    WHERE {
        ?person rdf:type :ActorDirector ;
                rdfs:label ?person_name .
    }
    """
    try:
        results = graph.query(query)
    except Exception as e:
        flash("Could not run that query.")
        flash("RDFLIB Error: {}".format(e))
        sparql_validate(query)
        return jena5()
    return show_result(results=results, template="jena5.html")

def getIndividuals(individualsClass):
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
    individuals = set(graph.subjects(RDF.type, individualsClass))
    result = []
    for individual in individuals:
        # Query for the label of each actor
        individual_label = list(graph.objects(individual, RDFS.label))
        if individual_label:
            label = individual_label[0]  # Assuming there's at least one label, and taking the first
        else:
            label = "No label found"

        result.append({'inidividual': individual, 'label': label})
    
    return result

@app.route("/jena7", methods=["GET"])
def jena7():
    owlrl.OWLRL_Semantics(graph,axioms=True, daxioms=True)
    onto = rdflib.Namespace("http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/")
    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    directors = getIndividuals(onto.Director)
    actors = getIndividuals(onto.Actor)
    genre = getIndividuals(onto.Genre)

    print(actors)

    #TODO display those lists in the UI

    return show_result(results=[], template="jena3.html") #TODO new template needed

@app.route("/jena8", methods=["GET"])
def jena7Results():
    DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    actors = {
        "include":[rdflib.term.URIRef('http://webprotege.stanford.edu/R8iJLOBHKGJAl537mt9QePx')],
        "exclude":[]
    }
    directors = {
        "include":[rdflib.term.URIRef('http://webprotege.stanford.edu/R8iJLOBHKGJAl537mt9QePx')],
        "exclude":[]
    }
    genres = {
        "include":[rdflib.term.URIRef('http://webprotege.stanford.edu/RBip9IYyVTRBaeZruOe3lSb')],
        "exclude":[rdflib.term.URIRef('http://webprotege.stanford.edu/RBXDmexPRMYRH61rDLkiHZg')]
    }

    actors_include_list = " ".join([f"<{individual}>" for individual in actors["include"]])
    actors_exclude_list = " ".join([f"<{individual}>" for individual in actors["exclude"]])
    directors_include_list = " ".join([f"<{individual}>" for individual in directors["include"]])
    directors_exclude_list = " ".join([f"<{individual}>" for individual in directors["exclude"]])
    genres_include_list = " ".join([f"<{individual}>" for individual in genres["include"]])
    genres_exclude_list = " ".join([f"<{individual}>" for individual in genres["exclude"]])
    query = f"""
    prefix : <http://www.semanticweb.org/adham/ontologies/2024/4/untitled-ontology-6/>
    SELECT 
        ?show_name
        (GROUP_CONCAT(DISTINCT(?actor_name); separator=", ") AS ?actors)
        (?director_name as ?director)
        (GROUP_CONCAT(DISTINCT(?genre_name); separator=", ") AS ?genres)
    WHERE {{
        ?show rdf:type :Show.

        ?show :hasActor ?actor.
        ?show :hasDirector ?director.
        ?show :hasGenre ?genre.

        ?show rdfs:label ?show_name.
        ?actor rdfs:label ?actor_name.
        ?director rdfs:label ?director_name.
        ?genre rdfs:label ?genre_name.

        FILTER EXISTS {{
            ?show :hasActor ?included_actor.
            FILTER (?included_actor IN({actors_include_list})).
        }}
        FILTER EXISTS {{
            ?show :hasDirector ?included_director.
            FILTER (?included_director IN({directors_include_list})).
        }}
        FILTER EXISTS {{
            ?show :hasGenre ?included_genre.
            FILTER (?included_genre IN({genres_include_list})).
        }}
        FILTER NOT EXISTS {{
            ?show :hasActor ?excluded_actor.
            FILTER (?excluded_actor IN ({actors_exclude_list})).
        }}
        FILTER NOT EXISTS {{
            ?show :hasDirector ?excluded_director.
            FILTER (?excluded_director IN ({directors_exclude_list})).
        }}
        FILTER NOT EXISTS {{
            ?show :hasGenre ?excluded_genre.
            FILTER (?excluded_genre IN ({genres_exclude_list})).
        }}
    }}
    GROUP BY ?show_name
    """

    return run_query(query=query, template="jena3.html")

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
