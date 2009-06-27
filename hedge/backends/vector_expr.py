"""Base facility for compiled vector expressions."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see U{http://www.gnu.org/licenses/}.
"""




import numpy
import pymbolic.mapper.substitutor
import hedge.optemplate
from pytools import memoize_method, Record




class DefaultingSubstitutionMapper(
        pymbolic.mapper.substitutor.SubstitutionMapper,
        hedge.optemplate.IdentityMapperMixin):
    def handle_unsupported_expression(self, expr):
        result = self.subst_func(expr)
        if result is not None:
            return result
        else:
            pymbolic.mapper.substitutor.SubstitutionMapper.handle_unsupported_expression(
                    self, expr)





class ConstantGatherMapper(
        hedge.optemplate.CombineMapper,
        hedge.optemplate.CollectorMixin):
    def map_algebraic_leaf(self, expr):
        return set()

    def map_constant(self, expr):
        return set([expr])




class KernelRecord(Record):
    pass




class CompiledVectorExpressionBase(object):
    def __init__(self, vec_exprs, is_vector_func, result_dtype_getter):
        self.vec_exprs = vec_exprs
        self.is_vector_func = is_vector_func
        self.result_dtype_getter = result_dtype_getter

        from hedge.optemplate import DependencyMapper
        from operator import or_
        dep_mapper = DependencyMapper(
                include_subscripts=True,
                include_lookups=True,
                include_calls="descend_args")
        deps = reduce(or_, (dep_mapper(ve) for ve in vec_exprs))

        self.vector_exprs = [dep for dep in deps if is_vector_func(dep)]
        self.scalar_exprs = [dep for dep in deps if not is_vector_func(dep)]
        self.vector_names = ["v%d" % i for i in range(len(self.vector_exprs))]
        self.scalar_names = ["s%d" % i for i in range(len(self.scalar_exprs))]

        self.constant_dtypes = [
                numpy.array(const).dtype
                for ve in vec_exprs
                for const in ConstantGatherMapper()(ve)]

        from pymbolic import var
        var_i = var("i")
        subst_map = dict(
                list(zip(self.vector_exprs, [var(vecname)[var_i]
                    for vecname in self.vector_names]))
                +list(zip(self.scalar_exprs,
                    [var(scaname) for scaname in self.scalar_names])))

        def subst_func(expr):
            try:
                return subst_map[expr]
            except KeyError:
                return None

        self.exprs = [
                DefaultingSubstitutionMapper(subst_func)(ve)
                for ve in vec_exprs]

    @memoize_method
    def get_kernel(self, vector_dtypes, scalar_dtypes):
        from pymbolic.mapper.stringifier import PREC_NONE
        from pymbolic.mapper.c_code import CCodeMapper

        elwise = self.elementwise_mod

        result_dtype = self.result_dtype_getter(
                dict(zip(self.vector_exprs, vector_dtypes)),
                dict(zip(self.scalar_exprs, scalar_dtypes)),
                self.constant_dtypes)

        from hedge.tools import is_obj_array
        args = [elwise.VectorArg(result_dtype, "_result%d" % i)
                for i in range(len(self.exprs))]

        code_mapper = CCodeMapper()
        expr_codes = [code_mapper(e, PREC_NONE) for e in self.exprs]
        code_lines = [
            "%s = %s;" % (
                get_c_declarator(
                    "%s%d" % (code_mapper.cse_prefix, i),
                    False, result_dtype),
                cse)
            for i, cse in enumerate(code_mapper.cses)
            ] + [
            "_result%d[i] = %s;" % (i, ec)
            for i, ec in enumerate(expr_codes)]

        args.extend(
                elwise.VectorArg(dtype, name)
                for dtype, name in zip(vector_dtypes, self.vector_names))
        args.extend(
                elwise.ScalarArg(dtype, name)
                for dtype, name in zip(scalar_dtypes, self.scalar_names))

        #print ",".join(args)
        #print "\n".join(code_lines)

        return KernelRecord(
                kernel=self.make_kernel_internal(args, "\n".join(code_lines)),
                result_dtype=result_dtype)
