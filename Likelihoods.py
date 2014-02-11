import os
from collections import OrderedDict as odict
import clik

likelihoods = ["commander_v4.1_lm49.clik",
               "CAMspec_v6.2TN_2013_02_26_dist.clik",
               "lowlike_v222.clik"]

class Likelihoods():

    def __init__(self, folder=None, likelihoods=None):
        self._likelihoods_names = (likelihoods if likelihoods else
                                   ["commander_v4.1_lm49.clik",
                                    "CAMspec_v6.2TN_2013_02_26_dist.clik",
                                    "lowlike_v222.clik"])
        # Initialize!
        self._likelihoods = dict([name,clik.clik(os.path.join(folder, name))]
                                 for name in self._likelihoods_names)
        # Read nuisance parameters
        self._nuisance_parameters = dict([lik_name,{}] for lik_name in self._likelihoods_names)
        for lik in self._likelihoods_names:
            names = self._likelihoods[lik].extra_parameter_names
            self._nuisance_parameters[lik] = ({} if not names else
                odict([[pname,None] for pname in names]))

    def set_nuisance(self, n_dict=None, n_file=None):
        """
        Set the value of the nuisance parameters.
        Specify a dictionary via "n_dict" as "nuisance['param']=value"
        or a file name which contains the parameter values in different lines as
        'param = value'.
        """
        assert n_dict or n_file and not(n_dict and n_file), \
            ("A dictionary of values as 'n_dict={...}' OR a file name as"+
             +"'n_file='...' must be specified.")
        if n_file:
            nuisance_dict = {}
            try:
                nui = open(n_file, "r")
            except IOError:
                raise IOError("Nuisance parameters file not found: "+n_file)
            err_par = "Some parameter definition is not correctly formatted: "
            for line in nui:
                if line.strip() and line.strip()[0] != "#":
                    aux = [a.strip() for a in line.split()]
                    assert aux[1] == "=", (
                        "Some parameter definition is not correctly formatted:"+
                        " line: '%s'")
                    par, val = aux[0], aux[2]
                    try :
                        val = float(val)
                    except ValueError:
                        raise ValueError("Some parameter definition is not correctly formatted:"+
                                         " line: '%s'")
                    nuisance_dict[par] = val
        if n_dict:
            nuisance_dict = n_dict
        # Both cases, fill values
        for lik in self._likelihoods_names:
            for p in self._nuisance_parameters[lik]:
                try:
                    self._nuisance_parameters[lik][p] = nuisance_dict[p]
                except KeyError:
                    raise KeyError("Nuisance parameter '%s' not defined!"%p)

    def get_loglik(self, CMBspectrum, verbose=False):
        # Check that nuisance parameters are defined (if one is, all are)
        for lik in self._likelihoods_names:
            if self._nuisance_parameters[lik]:
                assert self._nuisance_parameters[lik].values()[0], (
                    "Nuisance parameters not yet defined! Set their values using "+
                    "'Likelihoods.set_nuisance()'.")
        # Format of Clik :  TT EE BB TE TB EB ( l = 0, 1, 2, ... !!!)
        l = list(CMBspectrum.ll())
        pre = range(int(l[0]))
        l = np.array(pre + l)
        spectrum = np.zeros([len(l), 6])
        # NOTICE that this sets C_0 = C_1 = 0
        spectrum[2:, 0] = CMBspectrum.lCl("TT", units="muK", l_prefactor=False)
        spectrum[2:, 1] = CMBspectrum.lCl("EE", units="muK", l_prefactor=False)
        spectrum[2:, 3] = CMBspectrum.lCl("TE", units="muK", l_prefactor=False)
        # Prepare the vectors for the likelihoods:
        vectors = {}
        for lik in self._likelihoods_names:
            vectors[lik] = []
            # Which spectra
            which_cls = [int(i) for i in self._likelihoods[lik].has_cl]
            l_max     = self._likelihoods[lik].lmax
            assert len(l) >= max(l_max), (
                "Not enought multipoles for likelihood "+
                "'%s' : needs %d, got %d"%(lik, max(l_max), len(l)))
            for i, cli in enumerate(which_cls):
                if cli:
                    vectors[lik] += spectrum[:(1+l_max[i]), i].tolist()
            # Nuisance
            for par,val in self._nuisance_parameters[lik].items():
                vectors[lik].append(val)
        # Calculate the likelihood
        loglik = {}
        for lik in self._likelihoods_names:
            if verbose:
                print "*** Computing : "+lik
            loglik[lik] = self._likelihoods[lik](vectors[lik])
            if verbose:
                print "loglik  = ",loglik[lik]
                print "chi2eff = ",-2*loglik[lik]
        suma = sum(a[0] for a in loglik.values())
        if verbose:
            print "*** TOTAL :"
            print "loglik  = ",suma
            print "chi2eff = ",-2*suma
        return suma
