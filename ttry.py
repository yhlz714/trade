from tqsdk import TqApi, TqAccount, TargetPosTask, TqSim

api=TqApi(TqSim())
a=api.get_quote('SHFE.rb2010')
print('')