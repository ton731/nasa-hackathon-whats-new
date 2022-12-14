import os, glob
from spacepy import pycdf
import numpy as np
from tqdm import tqdm

def fillValue(array, windowSize, threshold):
    ### fill the value with the average of legal values besides
    ### when the value is missing (or exceeded the legal range)
    ### array: the array which'll be operated
    ### windowSize: range of besides shold be consider
    ### threshold: 
    for row in tqdm(range(len(array))):
        for col in range(len(array[row])):
            if array[row][col] < threshold:
                minCol = max(0, col - windowSize // 2)
                maxCol = min(len(array[row]) - 1, col + windowSize // 2)
                sum = 0
                num = 0
                for idx in range(minCol, maxCol + 1):
                    if array[row][idx] > threshold:
                        sum += array[row][idx]
                        num += 1

                try:
                    array[row][col] = sum/num
                except:
                    print(f"num = {num}")

    return array.T


def preprocessing(folderSet, keySet, storeFolder, year, windowSize, threshold):
    ### concatenate and clean up the data
    ### folderSet: the list of folder which contain the files to be concatenated
    ### keySet: specify the critical data we want to remain
    ### storeFolder: the concatenated files will be stored here
    ### year: specify the specific year files to be concatenate
    ### windowSize: refer to fillValue()
    ### threshold: refer to fillValue()

    for folder, keys in zip(folderSet, keySet):
        files = sorted(glob.glob(os.path.join(folder, "*_"+str(year) + '*.cdf')))

        for key in keys:
            subList = []
        
            for file in files:
                print(file)
                cdf_pycdf = pycdf.CDF(file)
                try:
                    subList.append(cdf_pycdf[key][:])
                except Exception as e:
                    print(f"error key {e}")
                    break

            subList = np.concatenate(subList, axis = 0)
            np.save(os.path.join(storeFolder, str(year) + "-mag-" + key + ".npy"), subList, allow_pickle=True, fix_imports=True)
            if key == 'B1GSE' or key == 'BGSE':
                subList = fillValue(subList.transpose(), windowSize, threshold)
            np.save(os.path.join(storeFolder, "filled-"+ str(year) + "-mag-" + key + ".npy"), subList, allow_pickle=True, fix_imports=True)
            del subList


if __name__ == "__main__":
    ### concate all cdf files in folder
    storeFolder = "./npyFiles"
    os.makedirs(storeFolder, exist_ok=True)

    folderMAG = "Data/dscovr-h0-mag"
    folderMFI = "Data/wind-mfi-mfi_h2"
    folderSWE = "Data/wind-swe-swe_h1"
    folderSet = [folderMAG, folderMFI, folderSWE]
    magKey = ['Epoch1', 'B1GSE']
    mfiKey = ['Epoch', 'BGSE']
    sweKey = ['Proton_Np_moment', 'Proton_V_moment', 'Proton_W_moment']
    keySet = [magKey, mfiKey, sweKey]

    windowSize = 10
    threshold = -1000000

    start_year = 2021
    end_year = 2021

    for year in range(start_year, end_year+1):

        preprocessing(folderSet, keySet, storeFolder, year, windowSize, threshold)
