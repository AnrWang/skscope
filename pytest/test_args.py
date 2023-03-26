import numpy as np
import pytest
import nlopt

from create_test_model import CreateTestModel
from scope import ScopeSolver, BaseSolver, GrahtpSolver, GraspSolver, IHTSolver


model_creator = CreateTestModel()
linear = model_creator.create_linear_model()

models = (linear,)
models_ids = ("linear",)
solvers = (ScopeSolver, BaseSolver)#, GrahtpSolver, GraspSolver, IHTSolver)
solvers_ids = ("scope", "Base")#, "GraHTP", "GraSP", "IHT")


@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
def test_nlopt_solver(model, solver_creator):
    """
    Custom nlopt solver
    """
    nlopt_solver = nlopt.opt(nlopt.LD_SLSQP, 1)
    nlopt_solver.set_ftol_rel(0.001)

    solver = solver_creator(
        model["n_features"], model["n_informative"], nlopt_solver=nlopt_solver
    )
    params = solver.solve(model["loss"])

    assert model["params"] == pytest.approx(params, rel=0.01, abs=0.01)


@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
def test_init_support_set(model, solver_creator):
    solver = solver_creator(model["n_features"], model["n_informative"])
    solver.solve(model["loss"], init_support_set=[0, 1, 2], jit=True)

    assert set(model["support_set"]) == set(solver.support_set)


@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
def test_init_params(model, solver_creator):
    solver = solver_creator(model["n_features"], model["n_informative"])
    solver.solve(model["loss"], init_params=np.ones(model["n_features"]), jit=True)

    assert set(model["support_set"]) == set(solver.support_set)

@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
@pytest.mark.parametrize("ic_type", ["aic", "bic", "gic", "ebic"])
def test_ic(model, solver_creator, ic_type):
    solver = solver_creator(
        model["n_features"],
        [0, model["n_informative"]],
        model["n_samples"],
        ic_type=ic_type,
    )
    solver.solve(model["loss"], jit=True)

    assert set(model["support_set"]) == set(solver.support_set)

@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
def test_cv_random_split(model, solver_creator):
    solver = solver_creator(
        model["n_features"],
        [0, model["n_informative"]],
        model["n_samples"],
        cv=2,
    )
    solver.solve(model["loss_data"], jit=True)

    assert set(model["support_set"]) == set(solver.support_set)

@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
def test_cv_given_split(model, solver_creator):
    n_fold = 2
    cv_fold_id = [i for i in range(n_fold)] * (model["n_samples"] // n_fold) + [
        i for i in range(model["n_samples"] % n_fold)
    ]
    solver = solver_creator(
        model["n_features"],
        [0, model["n_informative"]],
        model["n_samples"],
        cv=n_fold,
        cv_fold_id=cv_fold_id,
    )
    solver.solve(model["loss_data"], jit=True)

    assert set(model["support_set"]) == set(solver.support_set)


@pytest.mark.parametrize("model", models, ids=models_ids)
@pytest.mark.parametrize("solver_creator", solvers, ids=solvers_ids)
def test_no_autodiff(model, solver_creator):
    """
    Test that the user can provide the gradient and hessian
    """
    solver = solver_creator(model["n_features"], model["n_informative"])
    if str(solver)[:5] == "Scope":
        solver.solve(model["loss_numpy"], gradient=model["grad"], hessian=model["hess"])
    else:
        solver.solve(model["loss_numpy"], gradient=model["grad"])

    assert set(model["support_set"]) == set(solver.support_set)


def test_add_coverage():
    solver = ScopeSolver(
        linear["n_features"],
        gs_lower_bound=linear["n_informative"] - 1,
        gs_upper_bound=linear["n_informative"] + 1,
        group=[i for i in range(linear["n_features"])],
        screening_size=linear["n_features"],
        splicing_type="taper",
        path_type="gs",
        important_search=1,
        always_select=[linear["support_set"][0]],
        init_params_of_sub_optim=lambda x, data, index: x,
        console_log_level="error"
    )
    solver.solve(linear["loss"], jit=True)

    solver = ScopeSolver(
        linear["n_features"],
        group=[0] + [i for i in range(linear["n_features"]-1)],
        screening_size=0,
        path_type="gs",
        sample_size=linear["n_samples"],
        cv=2,
        file_log_level="error",
    )
    solver.solve(linear["loss_data"])

    solver = ScopeSolver(linear["n_features"], linear["n_informative"])
    solver.solve(**linear["cpp_model"], cpp=True)
    set1 = set(solver.support_set)
    solver.solve(linear["cpp_model"]["objective"], data=linear["cpp_model"]["data"], cpp=True)
    set2 = set(solver.support_set)
    
    assert set(linear["support_set"]) == set1
    assert set(linear["support_set"]) == set2