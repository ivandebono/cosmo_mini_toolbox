###################################################
# Class for manipulating chains and getting info  #
# independently from the code that generated them #
###################################################

import os
import numpy as np
import matplotlib.pyplot as plt
import re

from CLASS_tools import CMBspectrum_from_param_file_CLASS

class Chain():
    """
    Class for manipulating chains and getting info from them, independently from
    the code that generated them.

    Mandatory arguments:
    --------------------

    folder: str
        Folder in which the chain is stored.
        In the case of a 'MontePython' chain, it is enough to specify the folder.
        In the case of a 'CosmoMC' chain, a 'prefix' must also be given.


    Optional arguments:
    -------------------

    prefix: str
        Prefix of the chain files of a 'CosmoMC' chain.

    code: one of ["MontePython" (default), "CosmoMC", "CosmoMC+MultiNest", "CosmoMC+PolyChord"]
        Code with which the chain was generated (case insensitive).

    """
    def __init__(self, folder=None, prefix=None, code="MontePython"):
        # Check input
        assert os.path.isdir(folder), \
            "The chain folder provided is not really a folder."
        self._folder = folder
        self._prefix = prefix
        self._code = code.lower()
        # MontePython case
        if self._code == "montepython":
            self._load_params_montepython()
            self._chains = [os.path.join(self._folder, a)
                            for a in os.listdir(self._folder) if a[-4:]==".txt"]
        # CosmoMC case
        elif self._code == "cosmomc":
            self._load_params_cosmomc()
            self._chains = [os.path.join(self._folder, a)
                            for a in os.listdir(self._folder)
                            if re.match(self._prefix+"_[0-9]+\.txt", a)] 
        # CosmoMC+[MultiNest,PolyChord] case
        elif self._code in ("cosmomc+multinest", "cosmomc+polychord"):
            self._load_params_cosmomc()
            self._chains = [os.path.join(self._folder, a)
                            for a in os.listdir(self._folder)
                            if re.match(self._prefix+"\.txt", a)]
        else:
            raise ValueError("Code provided by keyword 'code' not known.")
        # Points
        individual_chains = []
        for chain in self._chains:
            # Handle empty files:
            if os.path.getsize(chain) == 0:
                continue
            individual_chains.append(np.loadtxt(chain))
        self._points = np.concatenate(individual_chains)
        # Scaling -- MontePython
        if self._code == "montepython":
            for i, param in enumerate(self.varying_parameters() +
                                      self.derived_parameters()):
                self._points[:,i+2] *= float(self._raw_params["parameter"][param][4])
        # LogLik better than ChiSq -- MultiNest
        if self._code in ("cosmomc+multinest", "cosmomc+polychord"):
            self._points[:,1] /= 2
        # Finding best fit(s) -- faster if done now (only once!)
        self._mloglik_sorted_points = sorted(self._points, key=lambda x: x[1])

    # Load parameters
    def _load_params_montepython(self):
        assert os.path.exists(self._folder) ,\
            "The chain folder does not exist: "+self._folder
        self._name = self._folder.strip("/").split("/")[-1]
        logparam = open(os.path.join(self._folder, "log.param"))
        cosmo_arguments = {}
        parameters      = {}
        path            = {}
        self._sorted_varying_params = [] # list of the (sorted) varying params
        self._sorted_derived_params = [] # list of the (sorted) derived params
        self._param_labels = {}          # list of parameter labels for plots
        for line in logparam:
            if not line.strip():
                continue
            if line.strip()[0] == "#":
                continue
            if "data.cosmo_arguments" in line:
                if ".update" in line:
                    continue
                left, right = line.split("=")
                key = left[1+left.find("["):left.find("]")].strip("'").strip('"')
                cosmo_arguments[key] = right.split(";")[0].strip()
            if "data.parameters" in line:
                left, right = line.split("=")
                key = left[1+left.find("["):left.find("]")].strip("'").strip('"')
                parameters[key] = [a.strip() for a in
                    right.split(";")[0].strip().lstrip("[").rstrip("]").split(",")]
                param_type = parameters[key][5].strip('"').strip("'")
                if param_type in ["cosmo", "nuisance"]:
                    self._sorted_varying_params.append(key)
                if param_type == "derived":
                    self._sorted_derived_params.append(key)
                self._param_labels[key] = key
            if "data.path" in line:
                left, right = line.split("=")
                if not "data.path" in left:
                    continue
                key = left[1+left.find("["):left.find("]")].strip("'").strip('"')
                path[key] = right.split(";")[0].strip()
        logparam.close()
        params = {"cosmo_argument": cosmo_arguments,
                  "parameter":      parameters,
                  "path":           path}
        self._raw_params = params
    def _load_params_cosmomc(self) :
        assert os.path.exists(self._folder) ,\
            "The chain folder does not exist: " + self._folder
        self._name = self._prefix
        logparam = open(os.path.join(self._folder, self._prefix+".inputparams"))
        cosmo_arguments = {}
        parameters      = {}
        for line in logparam :
            if line[0] == "#" :
                continue
            # Varying parameters
            if "param[" in line and "=" in line :
                left, right = line.split("=")
                paramname = left.split("[")[-1].strip()[:-1]
                parameters[paramname] = [a.strip() for a in right.strip().split()]
            # Cosmo code arguments (i.e. fixed)
            if not("param[") in line and "=" in line :
                left, right = [a.strip() for a in line.split("=")]
                paramname = left
                cosmo_arguments[paramname] = right
        logparam.close()
        params = {"cosmo_argument": cosmo_arguments,
                  "parameter":      parameters}
        self._raw_params = params
        # Columns in the chain files
        self._sorted_varying_params = [] # list of the (sorted) varying parameters
        self._sorted_derived_params = [] # list of the (sorted) derived parameters
        self._param_labels = {}          # list of parameter labels for plots
        with open(os.path.join(self._folder, self._prefix+".paramnames"), "r") as pfile:
            for line in pfile:
                param = line.split()[0].strip()
                if param[-1] == "*":
                    self._sorted_derived_params.append(param)
                else:
                    self._sorted_varying_params.append(param)
                self._param_labels[param] = r"%s"%line.split()[1].strip()


    # Get chain data in a code independent way
    def name(self):
        return self._name
    def varying_parameters(self):
        return self._sorted_varying_params
    def derived_parameters(self):
        return self._sorted_derived_params
    def parameters(self):
        return self.varying_parameters()+self.derived_parameters()
    def parameter_label(self, param):
        return self._param_labels[param]
    def set_parameter_labels(self, labels):
        """
        The argument 'labels' must be a dictionary of parameters (str)
        and their labels (str, possibly in LaTeX notation, e.g. r"$H_0$").

        Missing parameters in the dictionary are left to their default values.
        Unknown ones are ignored.

        Returns the list of parameter whose label was changed.
        """
        params = []
        for param, label in labels.items():
            if param in self.parameters():
                self._param_labels[param] = label
                params.append(param)
        return params
    def chain_files(self):
        return self._chains
    def index_of_param(self, param, chain=False):
        """
        Returns the index of the given parameter.

        If the keyword 'chain' is set to True (default: False) gives the index
        within a chain point row.
        """
        offset = 2 if chain else 0
        if param == "#" and chain:
            return 0
        elif param == "mloglik" and chain:
            return 1
        elif param in self.varying_parameters():
            return offset + self.varying_parameters().index(param)
        elif param in self.derived_parameters():
            return (offset + len(self.varying_parameters()) +
                    self.derived_parameters().index(param))
        else:
            raise ValueError("Unrecognized parameter: '"+str(param)+"'.")
    def points(self, param=None):
        """
        Possibilities:
        
        * param == None (or not defined) : all chain points, as rows
        * param == "#" : number of steps / (non-normalizaed) prob. of the sample
        * param == "mloglik" : minus log-likelihood
        * param == <param_name> : chain points for said parameter

        """
        if not param:
            return self._points
        else:
            return self._points[:, self.index_of_param(param, chain=True)]
    def get_min(self, param):
        """
        Gets the minimum value of the given parameter that the chain has reached.
        """
        return self.points(param=param).min()
    def get_max(self, param):
        """
        Gets the maximum value of the given parameter that the chain has reached.
        """
        return self.points(param=param).max()
    def get_limits(self, param):
        """
        Gets the limits *imposed* on the search for the given parameter
        (different from 'get_min', 'get_max').

        Output: [lower, upper], with 'None' where no limit was imposed.
        """
        if param in self.varying_parameters():
            limits = [None, None]
            for i in [1, 2]:
               lim = self._raw_params["parameter"][param][i].strip()
               if self._code == "montepython":
                   scale = float(self._raw_params["parameter"][param][4])
                   limits[i-1] = float(lim)*scale if lim != '-1' else None
               elif self._code == "cosmomc":
                   limits[i-1] = float(lim)
            return limits
        elif param in self.derived_parameters():
            raise ValueError("The parameter '%s' has no limits: "%param +
                             "it is a derived parameter.")
        else:
            raise ValueError("The parameter '%s' is not recognised."%param)
    def best_fit(self, how_many=1, param=None):
        """
        Returns the best fit point(s) of the chain, as many as the value of
        'how_many'.

        A parameter can be specified to get only its best fit value.
        """
        points = self._mloglik_sorted_points[:how_many]
        if param:
            return [p[self._index_of_param(param, chain=True)] for p in points]
        else:
            return points

    # Covariance matrix 
    def _calculate_covariance_matrix(self):
        """
        You shouldn't need to call this function, though you may want to test
        different calculation methods.
        """
        # total_steps = np.sum(self.points("#"))
        # weights = self.points("#")/total_steps
        # means = [np.sum(weights*self.points(p)) for p in
        #          self.varying_params()+self.derived_params()]
        # print means

        # For now, just read it from the .covmat file
        if self._code == "montepython":
            print ("TODO: at this point, the covmat is read from the file " +
                   "generated by MontePython's analysis routine, " +
                   "instead of calculated here!.")
            try:
                covmat = np.loadtxt(os.path.join(self._folder,
                                                 self._name + ".covmat"))
            except IOError:
                raise IOError("The '.covmat' file was not found. "+
                              "Maybe because the chain has never been analysed.")
            self._covmat = covmat
        else:
            raise NotImplementedError("Not implemented for '%s'"%self._code)
    def _assert_calculated_covmat(self):
        if not hasattr(self, "_covmat"):
            self._calculate_covariance_matrix()
    def covariance(self, param1=None, param2=None):
        """
        Returns the covariance between 'param1' and 'param2',
        or the full covariance matrix if called without arguments.
        """
        self._assert_calculated_covmat()
        if param1 and param2:
            return self._covmat[self.index_of_param(param1, chain=False),
                                self.index_of_param(param2, chain=False)]
        else:
            return self._covmat
    def variance(self, param):
        """
        Returns the variance of 'param'.
        """
        return self.covariance(param, param)
    def correlation(self, param1=None, param2=None):
        """
        Returns the correlation between 'param1' and 'param2',
        or the full correlation matrix if called without arguments.
        """
        self._assert_calculated_covmat()
        if param1 and param2:
            return (self.covariance(param1, param2) /
                    np.sqrt(self.variance(param1)*self.variance(param2)))
        else:
            corrmat = np.ones(shape=self._covmat.shape)
            for param1 in self.parameters():
                for param2 in self.parameters():
                    corrmat[self.index_of_param(param1),
                            self.index_of_param(param2)] = \
                        self.correlation(param1, param2)
            return corrmat
    def plot_correlation(self, params=None, save_file=None,
                         dpi=150, transparent=False, turn_labels=False,
                         fontsize_params=16):
        """
        Plots the correlation matrix.

        Arguments:
        ----------

        params: list of parameter names (default: None)
            If specified, plots the correlation matrix of only said parameters.

        save_file: str (default: None)
            File in which to save the plot. If not specified, the plot is "shown".

        dpi: int (default: 150)
            Resolution used if the plot is saved to a file

        transparent: bool (default: False)
            Makes the frame around the plot transparent.

        turn_labels: bool (default: False)
            Turn the parameter labels in the x axis, if they don't fit.

        fontsize_params: float (default: 16)
            Font size of the parameter labels.

        """
        if params:
            correlations = np.ones(shape=(len(params), len(params)))
            for i, param1 in enumerate(params):
                for j, param2 in enumerate(params):
                    correlations[i, j] = self.correlation(param1, param2)
        else:
            params = self.parameters()
            correlations = self.correlation()
        fig  = plt.figure()
        ax   = fig.add_subplot(111)
        imsh = ax.imshow(correlations, cmap="RdYlBu_r",
                         interpolation="nearest",# origin="lower",
                         aspect=1, zorder=0)
        # avoid too-dark colours
        clim = 1.5
        imsh.set_clim(-1*clim, clim)
        indices = [(i, j) for i in range(correlations.shape[0])
                          for j in range(correlations.shape[1])]
        for i, j in indices:
            if i != j:
                ax.annotate("$%.2f$"%correlations[i, j], xy=(j, i), 
                            horizontalalignment='center',
                            verticalalignment='center')
        # Hide the ticks
        ax.xaxis.set_ticks_position('none')
        ax.yaxis.set_ticks_position('none')
        plt.xticks(range(correlations.shape[0]),
                   [self.parameter_label(p) for p in params])
        plt.yticks(range(correlations.shape[1]),
                   [self.parameter_label(p) for p in params])
        plt.tick_params(labelsize=fontsize_params)
        if turn_labels:
            fig.autofmt_xdate()
        if not save_file:
            plt.show()
            return
        else:
            fig.frameon = transparent
            plt.savefig(save_file, transparent=transparent, dpi=dpi,
                        bbox_inches='tight', pad_inches=0.1)
            plt.close()    
            return

    # Create a CMBspectrum instance from a chain point
    def CMBspectrum_from_point(self, point, class_folder, override_params=None,
                               verbose=True):
        """
        TODO: document!

        If an argument in the .param file points to a file in a CLASS tree,
        the given one in the keyword 'class_folder' is used instead.
        """
        if self._code == "montepython":
            # 1. Create a parameters dictionary from the point
            parameters = {}
            # fixed arguments
            for p, v in self._raw_params["cosmo_argument"].items():
                path_cosmo_tag = "data.path['cosmo']"
                if path_cosmo_tag in v:
                    v2 = v.replace(path_cosmo_tag, class_folder)
                    v2 = v2.replace("'", "").replace('"', "").strip()
                    v2 = v2.split("+")
                    v2[-1] = v2[-1].lstrip("/")
                    v2 = os.path.join(*v2)
                    assert os.path.isfile(v2), \
                        ("The log.param file references a file %s "%v +
                         " which is not in the provided CLASS tree, " +
                         "i.e. the file %s does not exist."%v2)
                    v = v2
                parameters[p] = v.replace("'","").replace('"',"")
            # varying parameters
            for p, v in self._raw_params["parameter"].items():
                if eval(v[-1]) == "cosmo":
                    parameters[p] = point[self.index_of_param(p, chain=True)]
            # Override parameters
            for p in override_params:
                parameters[p] = override_params[p]
            # Create the CMBspectrum instance
            return CMBspectrum_from_param_file_CLASS(class_folder,
                                                     param_file=parameters,
                                                     verbose=verbose)           
        else:
            raise NotImplementedError("Not implemented for CosmoMC")

    # Create nuisance parameters file from chain point
    def nuisance_file_from_point(self, point, nuisance_file):
        """
        TODO: document!

        If 'nuisance_file' is set to None, returns the parameters dictionary.
        """
        if self._code == "montepython":
            # 1. Create a nuisance parameters dictionary from the point
            parameters = {}
            # fixed arguments
            for p, v in self._raw_params["parameter"].items():
                if eval(v[-1]) == "nuisance":
                    # fixed nuisance parameter
                    if v[-3] == 0:
                        parameters[p] = v[1]
                    # varying nuisance parameter
                    else:
                        parameters[p] = point[self.index_of_param(p, chain=True)]
            # 2. Create the file
            if nuisance_file:
                with open(nuisance_file, "w") as nfile:
                    nfile.write("\n".join([p+"="+str(v) for p, v in parameters]))
            else:
                return parameters
        else:
            raise NotImplementedError("Not implemented for CosmoMC")
