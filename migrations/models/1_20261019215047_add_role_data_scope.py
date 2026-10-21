from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "sys_role" ADD "data_scope" VARCHAR(16) NOT NULL DEFAULT 'SELF' /* 数据范围（SELF\/ALL 一期生效） */;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "sys_role" DROP COLUMN "data_scope";"""


MODELS_STATE = (
    "eJztXG1vo0gS/iuRP81K2TnewavVSfZM9tanZDKaZPZOOxmhBhqHCwYvNJmJVvnv19UY80"
    "7ANsbR8CVKuqtC81S/1FNVzd+TlW9hN3w7WzuTX87+nnhohekv2ebzswlar9NGaCDIcJlc"
    "+BTqaCNkhCRAJqHNNnJDTJssHJqBsyaO79FWL3JdaPRNKuh4y7Qp8py/IqwTf4nJPQ5ox5"
    "evtNnxLPwdh8mf6wfddrBr5QbqWPBs1q6TpzVrW3jkNyYITzN003ejlZcKr5/Ive9tpR2P"
    "QOsSezhABMO/J0EEw4fRbV40eaN4pKlIPMSMjoVtFLkk87o5DCaL95NqDEzfA/zoaEL2gk"
    "t4ys8CL6mSJiqSRkXYSLYt6nP8eum7x4rsKR9uJ8+sHxEUSzAYU9zMAMPL6oiU8XtPe4iz"
    "wtUg5jULYFob1bfJL0VoEyCbsE0aUnDTCdWM7l0kC7xBf1K5u0iRbeUumsq21BJz+mbWte"
    "c+bczZAPDt4uri5nZ29RH+8yoM/3IZcLPbC+gRWOtTofWN8hO0+3SRxItn+0/O/rO4/f0M"
    "/jz78/rDBcPVD8kyYE9M5W7/nMCYUER83fO/6cjKzLykNYGLSqbmjtbWjubOa56auRXFls"
    "DQBvcDm3sz+NTaa0Tuy3Z+d4+Cahsn8gXrUrAOY8+We+Ps4+Iu0qgUXcC21taKK/Rdd7G3"
    "pK/wyxnPcQ1m/GP26d3vs09vqFTBNh82XULc95yDc0VPJb/inAFAL7xoxUBd0FEhz8QlcF"
    "PtgeGl2Bq2SteJKQlszUzhd0veBWelBcrF+Z9irBQRDqPVCgVPXeZsRuWkcFUNje5FEjaN"
    "XXCVW81fuWH+yuX5S9Ay7AJtIn8K24GicSqAquJBtwPwP+2HjCcFDQYyH76hwNJLPb7g18"
    "mWu1bCqtiCPLRkUMFLwhsk/nhkOeTSX06qfPWk72WHHSR1dyPap9v+peAtRiEO2LCpXLGP"
    "DjZyK3voxkqisKrHX8NUdJJJWiFB35JOh0fsTr6OHGLkECOHGDnEyCHacAjYqvVOO2NG4+"
    "XtsWePTJUFjVpTENXjbpZ5/NjvHRyvrM7RnK/JpBlAuhNKnEVbpja3E1WQ2nAFqZ4sSCU+"
    "FnsKHYBNNQaGVRamlN1qnE0BVZDA0xZVVk8D1ldCwqqBzVFb0QSQ7d3mKy9obTiDoNVzBu"
    "hrH0KombLHDxu0QHavoAHfjow1cLEirCcf6HoZ0v3iXYIst8CUStWCyvoKG0HMt9qf/KnC"
    "0Q7+n/nKU0swqPumcBzdWFWN44c5+qkPtqZPoMzYqTr/a2Es6R0NTa7yrJJMC2jQVMr6xW"
    "9okyjLd5FkS9Yq/GkoiOm7hURHQVVo69831x/qIM7rFRD+7NG3/2I5Jjk/c52QfG2B9wbM"
    "g1CR7MYgiybbcdWWp1gDfoBHjnUky//N1ey/xZ3h3eX1vEgn4B/M62a54VsVTkOTDQqKp2"
    "YE26IzXlYsHMMPDoXSMvx4bCM4a2B0VKBTgDevNehhuPgILrDIwU/pRPgFI7KIAlAR6Ggm"
    "b6nWCdE3CWORtkicslNGghfaZCR4oT4jAX15hAtx2w4olzUHRlphp6RkyybF2FQhcKhqO+"
    "V+xDZAi/U4iyWY0+B3B4RzSscD1/FsvxpgGcvgIFuQB8II4hGCsBPAfJusJV+ftuRLeUsn"
    "1C3sYkCihPDc912MvJodOKdYQNmgmj3BXJ3iYUFQAWiIJFA3T7ZsgaFMd+WporQkJg3Yzq"
    "+vL3NH33xxWwD589X8goLPsKdCDsGp43ciybdP1BSXzsoh88h8wGRSkYMripy/lIoD8+ou"
    "aOhGqjJW0rVw1MYs2JgFG7NgYxas1yxYvCnrD7hTWDyvdRgfatdtEo5wGWxqSTyU06jMss"
    "JO5TS9RBtNP6oiWrVHz1a+r+hYec1UhsdUNAVfVARyJfOaXIiUG5DcaR+9OXSADH9fO3QV"
    "VG5Tc2dZi25eb/A8rmabAKnK29ldiTFbsROwU4FqqAInKposqaqscVuEy11NUM8X/wK0c/"
    "P7tNxUnw2q7Jv6cQb0BYc0kRp90NEHHdwpGX3Q0Qf90cxd8kG7VhEdtoJod79Tm1qQ3xZU"
    "Yd8SIqFN4YBQXzgglAoHYLBdME3kd8L0oMmpDKj71bn0ctVghb1IhyqLTlnZvNYB0oE77U"
    "qTX+3IMwHqMyNyXOJ44Vt44D8rw9KaaJlJKlxRJTHhWV3rOY6dMURrR3esTubJqLwG28T3"
    "RrYmWbxnfgSlEZqmaKdpFObYhabfLReW1+orVVNhjJuLy99qcjVJuhwWCAfMmB3pdIvSQO"
    "kfs8vLM8hIclzC6lQ55naSxsSmwyV2jsffCqlm4FwVC/IKeU+3Pvxk5s9eMCzYesPwPtN/"
    "dsQjvp4BVq+mtDV9BBu5XmCqyXsE2GXO6rbiZIuTHzCcIcC24a2Z4vOtGTbdoLbpIveBHy"
    "3vc0oJ46V4xik5tuhmN+9m75kzpxe55HMj/b55Cgle3WBCYkhKPDwvcP4SIQ+ZuB5m5Edq"
    "3sJVGqn5SM1Haj5S816pece80KkkhHgJyLgNXtquqaBePrTwiNyowgOuZyZbhVPiJfDYas"
    "6YBV7mRPNEyUhm2F3YSF5t8EhJFmzNYLuXwg2b9jyRDBHzrys808TvbnZIo0RqdENHN3Rw"
    "v2R0Q0c39Eczd+Vd/eHvmu/ukB7usvnhM0WeYz50zsBldHryg1pjqyiivDueYhs8xXo8xR"
    "Ke6JEeUUEXNFONwX1KeSrC1TAO8m773VrqJfuGV8jpdNdjq3AQZPdgpBzC8JUvo+2N3f7L"
    "EtcUj06Lfqsw9IpXZZEVI1rWaeygaxSG3/yg09cPsjrDr3rDVDrdJ+//exJOqFPq5TxWzN"
    "CX7h2lese7drRtaLh1pNgmK1MWW97t6u++UQHoMFrjIGG93bDOqZ7YLS8JiwjKFaByOb5X"
    "pxqIjy+Kgoy8f678gHZwUcg+WehUxKSaCU1e8wCE5pDOmQqJcOrywumnsMujNiso6UhtXg"
    "mVSZBqpK4hDkO43/uIg7AyBFn/GZKy5rBf0JBsHsUnMXyaBCocFFVoGfU9/BczbGqke534"
    "D9jT/0ecLsdxpfLQfg5dKlBgIkCYV2bcMY4LSBhLDG8z+XysRg/wndjPQW5kD1FXcqiSku"
    "TSwGsvKUneo1hSUqi/ydeVZApHijUlhZKTvetK4m2wMWo/w4Fj3k+qvvwb95w3Re5RKjPG"
    "7Q84EfuO29eegvWbdf3x12NN4J4o9s/nYWl0AHEj/joB7CU5T59IKj+JU5+ez6gMlaA/yD"
    "HTa+p90KTw8/8BReGenw=="
)
