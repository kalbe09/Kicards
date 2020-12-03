from flask import render_template, redirect, url_for, abort, flash, jsonify, make_response, request, current_app
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from ..models.users import User
from ..models.category import Category
from ..models.flashcard_collections import Collection
from ..models.flashcard import Flashcard
from . import main
from .. import db
from .forms import CollectionForm, FlashcardForm, EditFlashcardForm, FlashcardCategoryForm
from random import choice
import datetime


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASHCARD_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' %
                (query.statement, query.parameters, query.duration, query.context))
    return response


@main.route('/')
def index():
    if current_user.is_authenticated:
        collections = current_user.collections.order_by(Collection.prio.desc()).all()
    else:
        collections = []
    return render_template('index.html', collections=collections)


@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    collections = current_user.collections.order_by(Collection.prio.desc()).all()
    return render_template('user.html', user=user, collections=collections)




# *********************************************************************************************************************
# Add Collections, Categories, Flashcards
# *********************************************************************************************************************

# Collections***********************************************************************************************************
@main.route('/add-collection', methods=['GET', 'POST'])
@login_required
def add_collection():
    form = CollectionForm()
    
    # After pressing the button
    if form.validate_on_submit():
        now = datetime.datetime.now()
        now = datetime.date(now.year, now.month, now.day)

        # Validate entered duedate
        if form.duedate.data != None:
            if form.duedate.data < now:
                flash("Der Fälligkeitstermin liegt in der Vergangenheit")
                return render_template('add_collection.html', form=form)            
            
        # Save Category ?????
        category = Category.query.filter_by(name=form.category.data).first()
        if category is None:
            category = Category(name=form.category.data, duedate=form.duedate.data)
            
        # Add attributes to the new collection
        collection = Collection(name=form.name.data, duedate=form.duedate.data, prio=form.prio.data)
        collection.categories.append(category)
        collection.user = current_user

        # update database
        db.session.add(collection)
        db.session.commit()

        # Short notice and redirection to home
        flash('Fach hinzugefügt')

        return redirect(url_for('.index'))
    # for the template add_collection.html
    return render_template('add_collection.html', form=form)


# Categories********************************************************************************************
@main.route('/add-category/<int:id>/add-category', methods=['GET', 'POST'])
@login_required
def add_category(id):
    form = FlashcardCategoryForm()
    
    # Determine the current collection
    flashcardcollection = Collection.query.get_or_404(id)
    
    # After pressing the button
    if form.validate_on_submit():
        now = datetime.datetime.now()
        now = datetime.date(now.year, now.month, now.day)
        
        # Validate entered duedate
        if form.duedate.data != None:
            if form.duedate.data < now:
                flash("Der Fälligkeitstermin liegt in der Vergangenheit")
                return render_template('add_category.html', form=form, name=flashcardcollection.name)
        
        # create new category and put it in the list of his collection
        category = Category(name=form.name.data, duedate=form.duedate.data, prio=form.prio.data)
        flashcardcollection.categories.append(category)
        
        # update database
        db.session.add(flashcardcollection)
        db.session.commit()
        
        # Short notice and redirection to home
        flash('Lektion hinzugefügt')
        return redirect(url_for('.flashcardcollection', id=flashcardcollection.id))
        # for the template add_category.html
    return render_template('add_category.html', form=form, name=flashcardcollection.name)
        
        
        
       

# Flashcards************************************************************************************************
@main.route('/flashcardcollection/<int:id>/add-flashcard', methods=['GET', 'POST'])
@login_required
def add_flashcard(id):
    form = FlashcardForm()
    
    # Determine the current collection and category
    collection = Collection.query.get_or_404(id)
    category = Collection.query.get_or_404(id)

    # After pressing the button
    if form.validate_on_submit():

        # Add attributes to the new collection
# elegantere Lösung??????
        card = Flashcard(question=form.question.data, 
            answer=form.answer.data,
            category_id=id, collection_id = collection.name)


        collection.flashcards.append(card)
        category.flashcards.append(card)

        # update database
        db.session.add(collection)
        db.session.commit()
        
        
        # Short notice and redirection to home
        flash('Karteikarte wurde zum Fach {0} hinzugefügt'.format(collection.name))        
        return redirect(url_for('.add_flashcard', id=collection.id))
    
    # for the template add_flashcard.html
    return render_template('add_flashcard.html', form=form, name=collection.name)

# *********************************************************************************************************************
# Get Category
# *********************************************************************************************************************


# Categories filtered by names ****************************************************************************************
@main.route('/get-category', methods=['GET', 'POST'])
@login_required
def get_category():
    return jsonify({
        'category': [category.name for category in Category.query.order_by(Category.name).all()]
    })



# Flashcards for collection id ***************************************************************************************
@main.route('/flashcardcollection/<int:id>/')
@login_required
def flashcardcollection(id):
    flashcardcollection = Collection.query.get_or_404(id)
    
    catid = request.args.get('catid')
    if catid != 'Null':
        flashcards = flashcardcollection.flashcards.filter_by(wrong_answered=False, right_answered=False).all()
    elif catid == 'wrong_ones':
        flashcards = flashcardcollection.flashcards.filter_by(wrong_answered=True, right_answered=False).all()
    else:
        abort(404)
    return render_template('single_collection.html', flashcardcollection=flashcardcollection)

# Flashcards for collection colid and category catid **************************************************************
@main.route('/category/<int:catid>')
@login_required
def getcards_catid(catid):
    category = Category.query.get_or_404(catid)
    flashcards = category.flashcards.filter_by(wrong_answered=False, right_answered=False).all()

    #catid = request.args.get('catid')
    if catid != 'Null':
        flashcards = flashcardcollection.flashcards.filter_by(wrong_answered=False, right_answered=False).all()
    elif catid == 'wrong_ones':
        flashcards = flashcardcollection.flashcards.filter_by(wrong_answered=True, right_answered=False).all()
    else:
        abort(404)
    return render_template('single_collection.html', flashcardcollection=flashcardcollection)


# Categories for collection id**********************************************************************************
@main.route('/flashcardcategory/<int:id>')
@login_required
def flashcardcategory(collId, catid):
    flashcardcollection = Collection.query.get_or_404(collId)
    category = flashcardcollection.categories.filter_by(id=catid).first()
    return render_template('flashcardcategory.html', flashcardcollection=flashcardcollection, Category=category)


# Single flashcard for collection id ****************************************************************************************
@main.route('/flashcardcollection/<int:collId>/flashcard/<int:cardId>')
@login_required
def flashcard(collId, cardId):
    flashcardcollection = Collection.query.get_or_404(collId)
    flashcard = flashcardcollection.flashcards.filter_by(id=cardId).first()
    if flashcard is None:
        abort(404)
    return render_template('flashcard.html', flashcardcollection=flashcardcollection, flashcard=flashcard)


# *********************************************************************************************************************
# Delete 
# *********************************************************************************************************************

@main.route('/flashcardcollection/<int:id>/delete')
@login_required
def delete_flashcardcollection(id):
    flashcardcollection = Collection.query.get_or_404(id)
    db.session.delete(flashcardcollection)
    db.session.commit()
    flash('Fach {0} wurde gelöscht'.format(flashcardcollection.name))
    return redirect(request.referrer)

@main.route('/flashcardcollection/<int:collId>/delete-flashcard/<int:cardId>')
@login_required
def delete_card(collId, cardId):
    flashcard = Flashcard.query.get_or_404(cardId)
    db.session.delete(flashcard)
    db.session.commit()
    return redirect(url_for('.flashcardcollection', id=collId))

# *********************************************************************************************************************
# Edit 
# *********************************************************************************************************************

@main.route('/flashcardcollection/<int:collId>/flashcard/<int:cardId>/edit', methods=['GET', 'POST'])
@login_required
def edit_flashcard(collId, cardId):
    form = EditFlashcardForm()
    flashcardcollection = Collection.query.get_or_404(collId)
    flashcard = flashcardcollection.flashcards.filter_by(id=cardId).first()
    if flashcard is None:
        abort(404)
    if form.validate_on_submit():
        flashcard.question = form.question.data
        flashcard.answer = form.answer.data
        db.session.add(flashcard)
        db.session.commit()
        flash('Flashcard was updated.')
        return redirect(url_for('.flashcard', collId=collId, cardId=cardId))
    form.question.data = flashcard.question
    form.answer.data = flashcard.answer
    return render_template('edit_flashcard.html', form=form, flashcard=flashcard)



# *********************************************************************************************************************
# Learning 
# *********************************************************************************************************************

@main.route('/flashcardcollection/<int:id>/learn')
@login_required
def learn(id):
    flashcardcollection = Collection.query.get_or_404(id)
    mode = request.args.get('mode')
    if mode == 'normal':
        flashcards = flashcardcollection.flashcards.filter_by(wrong_answered=False, right_answered=False).all()
    elif mode == 'wrong_ones':
        flashcards = flashcardcollection.flashcards.filter_by(wrong_answered=True, right_answered=False).all()
    elif mode == 'bad_ones':
        #flash(flashcardcollection.flashcards.quote)
        flashcards = flashcardcollection.flashcards.order_by(Flashcard.quote.asc()).limit(50).all()
    else:
        abort(404)
    if not flashcards:
        flash('No Cards to learn. Please reset the Cards or learn the Wrong ones if there are any.')
        return redirect(url_for('.flashcardcollection', id=id))
    else:
        flashcard = choice(flashcards)
    return render_template('learn.html', flashcard=flashcard, collection=flashcardcollection)


@main.route('/flashcardcollection/<int:id>/reset-cards')
@login_required
def reset_cards(id):
    coll = Collection.query.get_or_404(id)
    for card in coll.flashcards.all():
        card.wrong_answered = False
        card.right_answered = False
        #card.sum_right_answered = 0
        #card.sum_wrong_answered = 0
    db.session.add(coll)
    db.session.commit()
    return redirect(url_for('.flashcardcollection', id=id))



@main.route('/flashcardcollection/<int:collId>/learn/<int:cardId>/wrong')
@login_required
def wrong_answer(collId, cardId):
    flashcard = Flashcard.query.get_or_404(cardId)
    flashcard.wrong_answered = True
    flashcard.right_answered = False
    flashcard.sum_wrong_answered += 1
    flashcard.sum_answered +=1
    flashcard.quote = round(flashcard.sum_wrong_answered/flashcard.sum_answered, 3)

# Einstellungsmöglichkeiten, was passiert mit phase wenn falsche Antwort
# flashcard.phase = 0
    
    flashcard.lastdate = datetime.datetime.now().strftime("%d.%m.%Y")
# flashcard.nextdate = phase * faktor
    
    # database update    
    db.session.add(flashcard)
    db.session.commit()
    
    # next card
    return redirect(url_for('.learn', id=collId, mode=request.args.get('mode')))


@main.route('/flashcardcollection/<int:collId>/learn/<int:cardId>/right')
@login_required
def right_answer(collId, cardId):
    flashcard = Flashcard.query.get_or_404(cardId)
    flashcard.wrong_answered = False
    flashcard.right_answered = True
    flashcard.sum_right_answered += 1
    flashcard.sum_answered +=1
    flashcard.quote = round(flashcard.sum_wrong_answered/flashcard.sum_answered, 3)
# flashcard.phase += 1

    flashcard.lastdate = datetime.datetime.now().strftime("%d.%m.%Y")
# flashcard.nextdate = phase * faktor

    # database update
    db.session.add(flashcard)
    db.session.commit()
    
    # next card
    return redirect(url_for('.learn', id=collId, mode=request.args.get('mode')))