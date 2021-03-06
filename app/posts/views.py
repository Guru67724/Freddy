from flask import Blueprint, request, jsonify, make_response
from app.posts.models import Posts, PostsSchema
from flask_restful import Api
from app.baseviews import Resource
from app.basemodels import db
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError
from app.terms.models import Terms

posts = Blueprint('posts', __name__)
# http://marshmallow.readthedocs.org/en/latest/quickstart.html#declaring-schemas
# https://github.com/marshmallow-code/marshmallow-jsonapi
schema = PostsSchema(strict=True)
api = Api(posts)

# Posts
class CreateListPosts(Resource):
    """http://jsonapi.org/format/#fetching
    A server MUST respond to a successful request to fetch an individual resource or resource collection with a 200 OK response.
    A server MUST respond with 404 Not Found when processing a request to fetch a single resource that does not exist, except when the request warrants a 200 OK response with null as the primary data (as described above)
    a self link as part of the top-level links object"""

    def get(self):
        posts_query = Posts.query.all()
        results = schema.dump(posts_query, many=True).data
        return results

    """http://jsonapi.org/format/#crud
    A resource can be created by sending a POST request to a URL that represents a collection of posts. The request MUST include a single resource object as primary data. The resource object MUST contain at least a type member.
    If a POST request did not include a Client-Generated ID and the requested resource has been created successfully, the server MUST return a 201 Created status code"""

    def post(self):
        raw_dict = request.get_json(force=True)
        try:
            schema.validate(raw_dict)
            request_dict = raw_dict['data']['attributes']
            post = Posts(request_dict['author'], request_dict['title'], request_dict['slug'], request_dict['content'], request_dict[
                         'excerpt'], request_dict['status'], request_dict['type'], request_dict['parent'], request_dict['path'])
            post_terms = request_dict['term_ids']
            for post_term in post_terms:
                term=Terms.query.get(post_term)
                post.terms.append(term)
            post.add(post)

            # Should not return password hash
            query = Posts.query.get(post.id)
            results = schema.dump(query).data
            return results, 201

        except ValidationError as err:
            resp = jsonify({"error": err.messages})
            resp.status_code = 403
            return resp

        except SQLAlchemyError as e:
            db.session.rollback()
            resp = jsonify({"error": str(e)})
            resp.status_code = 403
            return resp


class GetUpdateDeletePost(Resource):

    """http://jsonapi.org/format/#fetching
    A server MUST respond to a successful request to fetch an individual resource or resource collection with a 200 OK response.
    A server MUST respond with 404 Not Found when processing a request to fetch a single resource that does not exist, except when the request warrants a 200 OK response with null as the primary data (as described above)
    a self link as part of the top-level links object"""

    def get(self, id):
        post_query = Posts.query.get_or_404(id)
        result = schema.dump(post_query).data
        post_term_ids = [term.id for term in post_query.terms]
        result['data']['attributes']['term_ids'] = post_term_ids
        return result

    """http://jsonapi.org/format/#crud-updating"""

    def patch(self, id):
        post = Posts.query.get_or_404(id)
        raw_dict = request.get_json(force=True)
        try:
            schema.validate(raw_dict)
            #current post terms
            post_terms=[]
            for term in post.terms:
                post_terms.append(term.id)
            request_dict = raw_dict['data']['attributes']

            for key, value in request_dict.items():
                if key == "terms":
                    continue
                if key == "term_ids":
                    for term_id in value:
                        if term_id not in post_terms:
                            term=Terms.query.get(term_id)
                            post.terms.append(term)
                    #Remove old post terms which are not included in the update.
                    for post_term_id in post_terms:
                        if post_term_id not in value:
                              term=Terms.query.get(post_term_id)
                              post.terms.remove(term)

                setattr(post, key, value)

            post.update()
            return self.get(id)

        except ValidationError as err:
            resp = jsonify({"error": err.messages})
            resp.status_code = 401
            return resp

        except SQLAlchemyError as e:
            db.session.rollback()
            resp = jsonify({"error": str(e)})
            resp.status_code = 401
            return resp

    # http://jsonapi.org/format/#crud-deleting
    # A server MUST return a 204 No Content status code if a deletion request
    # is successful and no content is returned.
    def delete(self, id):
        post = Posts.query.get_or_404(id)
        try:
            delete = post.delete(post)
            response = make_response()
            response.status_code = 204
            return response

        except SQLAlchemyError as e:
            db.session.rollback()
            resp = jsonify({"error": str(e)})
            resp.status_code = 401
            return resp


api.add_resource(CreateListPosts, '.json')
api.add_resource(GetUpdateDeletePost, '/<int:id>.json')
